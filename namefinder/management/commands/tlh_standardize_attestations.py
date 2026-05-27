import csv
import difflib
import json
import re
from collections import defaultdict
from pathlib import Path

import duckdb
from django.core.management.base import BaseCommand

from namefinder.models import Determinative, DeterminativeVariant, Instance
from namefinder.models import Name as NameModel


SUPPORTED_SERIES = {"KBo", "KUB", "ABoT", "CHDS", "DAAM", "HKM", "IBoT", "VSNF"}


def normalize_fragment_reference(value):
    if not value:
        return ""
    value = re.sub(r"\{[^}]+\}", "", value)
    value = re.sub(r"\s+", " ", value.replace("_", " ")).strip()
    value = re.sub(r"^Kbo\b", "KBo", value)
    value = re.sub(r"^KBO\b", "KBo", value)
    value = re.sub(r"^KB0\b", "KBo", value)
    return value


def expand_reference_variants(value):
    normalized = normalize_fragment_reference(value)
    variants = set()
    if not normalized:
        return variants
    variants.add(normalized)
    variants.add(normalized.replace(" + ", "+"))
    variants.add(normalized.replace("+", " + "))

    pieces = re.split(r"\s*\(\+\)\s*|\s*\+\s*", normalized)
    for piece in pieces:
        piece = piece.strip()
        if piece:
            variants.add(piece)
    return {variant for variant in variants if variant}


def normalize_prime(value):
    return (
        value.replace("’", "′")
        .replace("'", "′")
        .replace("´", "′")
        .replace("`", "′")
    )


def clean_line_text(value):
    value = normalize_prime((value or "").strip())
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"[\[\]!]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def roman_upper(token):
    return token.upper() if token else ""


def parse_line_parts(value):
    normalized = normalize_fragment_reference(normalize_prime(value or ""))
    cleaned = re.sub(r"[\[\]!]", "", normalized)
    cleaned = cleaned.replace('""', "′").replace("″", "′")
    side_match = re.search(r"\b(Vs\.?|Rs\.?|obv\.?|rev\.?)\b", cleaned, flags=re.IGNORECASE)
    side = None
    if side_match:
        token = side_match.group(1).lower().rstrip(".")
        if token in {"vs", "obv"}:
            side = "Vs."
        elif token in {"rs", "rev"}:
            side = "Rs."
    column_match = re.search(r"\b(i|ii|iii|iv|v|vi|vii|viii|ix|x)\b", cleaned, flags=re.IGNORECASE)
    column = column_match.group(1).upper() if column_match else None
    numbers = [re.sub(r"\s+", "", match).replace('"', "′") for match in re.findall(r"\d+[a-z]?\s*[′\"]?", cleaned, flags=re.IGNORECASE)]
    number = numbers[-1] if numbers else None
    if number:
        number = number.replace('"', "′")
    lowered = cleaned.lower()
    edge = None
    if lowered.startswith(("lk. kol", "l. kol", "l. col", "lk. rd", "l. rd", "l.e.", "lo.e.")):
        edge = "left_col"
    elif lowered.startswith(("rk. kol", "r. kol", "r. col", "rk. rd", "r. rd", "r.e.", "ru.e.")):
        edge = "right_col"
    return {"side": side, "column": column, "number": number, "numbers": numbers, "edge": edge}


def parse_line_targets(raw_line):
    text = clean_line_text(raw_line).lower()
    if not text:
        return []

    side = None
    if "obv" in text or "vs" in text:
        side = "Vs."
    elif "rev" in text or "rs" in text:
        side = "Rs."

    edge = None
    if any(token in text for token in ("l. col", "l.col", "lk.", "l. rd", "lk. rd", "l.e.", "lo.e.")):
        edge = "left_col"
    elif any(token in text for token in ("r. col", "r.col", "rk.", "r. rd", "rk. rd", "r.e.", "ru.e.")):
        edge = "right_col"

    column_match = re.search(r"\b(i{1,4}|vi{0,3}|v)\b", text)
    column = roman_upper(column_match.group(1)) if column_match else None

    numbers = re.findall(r"\d+\s*′?", text)
    targets = []
    prefix = " ".join(part for part in [side, column] if part)
    for number in numbers:
        number = re.sub(r"\s+", "", normalize_prime(number))
        targets.append(
            {
                "label": " ".join(part for part in [prefix, number] if part).strip(),
                "side": side,
                "edge": edge,
                "column": column,
                "number": number,
            }
        )

    deduped = []
    seen = set()
    for target in targets:
        key = (target["side"], target["column"], target["number"])
        if key not in seen:
            seen.add(key)
            deduped.append(target)
    return deduped


def parse_json_list(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def canonical_determinative(dets):
    for det in dets:
        low = re.sub(r"[<>{}\\[\\]()/〈〉\\s.-]+", "", (det or "").lower())
        if low.startswith("m"):
            return "m"
        if low.startswith("f"):
            return "f"
        if low.startswith("d"):
            return "d"
        if "uru" in low:
            return "URU"
        if "kur" in low:
            return "KUR"
        if "ḫursag" in low or "hursag" in low:
            return "ḪUR.SAG"
        if "íd" in low or "id" == low:
            return "ÍD"
    return ""


def matches_name_type(instance_type, xml_content, dets):
    xml_content = (xml_content or "").upper()
    det = canonical_determinative(dets)
    if instance_type == "person":
        return any(marker in xml_content for marker in ("PNM", "PN.")) or det in {"m", "f"}
    if instance_type == "deity":
        return any(marker in xml_content for marker in ("DNM", "DN.")) or det == "d"
    if instance_type == "place":
        return any(marker in xml_content for marker in ("GNM", "GN.")) or det in {"URU", "KUR", "ÍD", "ḪUR.SAG"}
    return any(marker in xml_content for marker in ("NM", "PN.", "DN.", "GN.")) or bool(det)


def strip_personal_determinative(spelling, det):
    spelling = (spelling or "").strip()
    if det in {"m", "f", "d"}:
        spelling = re.sub(r"^(m|f|d)(\.)?", "", spelling, flags=re.IGNORECASE)
    return spelling.strip()


def extract_name_lemmas(xml_content, instance_type):
    xml_content = xml_content or ""
    target_prefix = {
        "person": "PN",
        "deity": "DN",
        "place": "GN",
    }.get(instance_type, "N")
    lemmas = []
    for lemma, tag in re.findall(r"@([^@]+)@([^@<\"]+)", xml_content):
        if target_prefix in tag.upper():
            lemmas.append(lemma)
    return lemmas


def normalize_name_value(value):
    return NameModel.normalize_for_search(value or "")


def candidate_name_keys(candidate, instance_type):
    values = [
        candidate.get("spelling", ""),
        candidate.get("raw_word", ""),
        candidate.get("transliteration", ""),
    ]
    values.extend(candidate.get("lemmas", []))

    keys = set()
    for value in values:
        normalized = normalize_name_value(value)
        if normalized:
            keys.add(normalized)
            if instance_type == "place":
                keys.add(normalized.replace("uru", "").replace("kur", ""))
            if instance_type == "deity":
                keys.add(normalized.replace("d", "", 1))
    return {key for key in keys if key}


def score_candidate(expected_keys, candidate_keys):
    best = 0.0
    for expected in expected_keys:
        for candidate in candidate_keys:
            if not expected or not candidate:
                continue
            if expected == candidate:
                best = max(best, 1.0)
                continue
            if expected in candidate or candidate in expected:
                best = max(best, 0.92)
            best = max(best, difflib.SequenceMatcher(None, expected, candidate).ratio())
    return best


def build_candidate_record(line, word, instance_type):
    det = canonical_determinative(word["determinatives"])
    spelling = strip_personal_determinative(word["clean_content"] or word["transliteration"], det)
    if not spelling:
        return None
    return {
        "line_number_raw": line["line_number_raw"],
        "line_id": line["line_id"],
        "word_order": word["word_order"],
        "spelling": spelling,
        "determinative": det,
        "raw_word": word["clean_content"] or word["transliteration"],
        "transliteration": word["transliteration"] or "",
        "lemmas": extract_name_lemmas(word["xml_content"], instance_type),
    }


class TLHMatcher:
    def __init__(self, db_path):
        self.con = duckdb.connect(str(db_path), read_only=True)
        self.reference_to_docs = defaultdict(list)
        self.doc_lines = {}
        self.line_words = {}
        self._load_reference_index()

    def _load_reference_index(self):
        rows = self.con.execute(
            """
            SELECT DISTINCT reference, doc_id, manuscripts_raw
            FROM (
                SELECT m.reference AS reference, m.doc_id AS doc_id, d.manuscripts_raw AS manuscripts_raw
                FROM manuscripts m
                LEFT JOIN documents d ON d.doc_id = m.doc_id
            )
            WHERE reference IS NOT NULL AND reference != ''
            """
        ).fetchall()
        for reference, doc_id, manuscripts_raw in rows:
            for variant in expand_reference_variants(reference):
                self.reference_to_docs[variant].append(doc_id)
            for variant in expand_reference_variants(doc_id):
                self.reference_to_docs[variant].append(doc_id)
            for variant in expand_reference_variants(manuscripts_raw):
                self.reference_to_docs[variant].append(doc_id)

        for key, docs in list(self.reference_to_docs.items()):
            deduped = []
            seen = set()
            for doc in docs:
                if doc not in seen:
                    seen.add(doc)
                    deduped.append(doc)
            self.reference_to_docs[key] = deduped

    def docs_for_reference(self, reference):
        return self.reference_to_docs.get(normalize_fragment_reference(reference), [])

    def load_lines(self, doc_id):
        if doc_id in self.doc_lines:
            return self.doc_lines[doc_id]

        rows = self.con.execute(
            """
            SELECT line_id, line_order, line_number_raw, transliteration_plain
            FROM lines
            WHERE doc_id = ?
            ORDER BY line_order
            """,
            [doc_id],
        ).fetchall()
        lines = []
        for line_id, line_order, line_number_raw, transliteration_plain in rows:
            normalized = normalize_fragment_reference(normalize_prime(line_number_raw or ""))
            lines.append(
                {
                    "line_id": line_id,
                    "line_order": line_order,
                    "line_number_raw": line_number_raw or "",
                    "normalized_label": normalized,
                    "parts": parse_line_parts(line_number_raw or ""),
                    "transliteration_plain": transliteration_plain or "",
                }
            )
        self.doc_lines[doc_id] = lines
        return lines

    def load_words(self, line_id):
        if line_id in self.line_words:
            return self.line_words[line_id]

        rows = self.con.execute(
            """
            SELECT word_order, clean_content, transliteration, determinatives, xml_content
            FROM words
            WHERE line_id = ?
            ORDER BY word_order
            """,
            [line_id],
        ).fetchall()
        words = []
        for word_order, clean_content, transliteration, determinatives, xml_content in rows:
            words.append(
                {
                    "word_order": word_order,
                    "clean_content": clean_content or "",
                    "transliteration": transliteration or "",
                    "determinatives": parse_json_list(determinatives),
                    "xml_content": xml_content or "",
                }
            )
        self.line_words[line_id] = words
        return words

    def match_instance(self, instance):
        fragment_ref = instance.fragment.series_fragment
        docs = self.docs_for_reference(fragment_ref)
        if not docs:
            return {"status": "no_doc", "fragment_ref": fragment_ref}

        targets = parse_line_targets(instance.line)
        if not targets:
            return {
                "status": "unparsed_line",
                "fragment_ref": fragment_ref,
                "doc_ids": docs,
                "targets": [],
            }

        doc_matches = []
        for doc_id in docs:
            lines = self.load_lines(doc_id)
            target_hits = {}
            for target in targets:
                target_num = (target["number"] or "").rstrip("′")
                hits = [
                    line for line in lines
                    if any(re.sub(r"[a-z]$", "", num.rstrip("′"), flags=re.IGNORECASE) == target_num for num in (line["parts"].get("numbers") or []))
                    and (not target["side"] or line["parts"]["side"] == target["side"])
                    and (
                        not target["column"]
                        or line["parts"]["column"] == target["column"]
                        or (target["edge"] and not line["parts"]["column"])
                    )
                    and (not target["edge"] or line["parts"]["edge"] == target["edge"])
                ]
                if hits:
                    target_hits[target["label"]] = hits
            if len(target_hits) == len(targets):
                doc_matches.append((doc_id, target_hits))

        if not doc_matches:
            return {
                "status": "line_not_found",
                "fragment_ref": fragment_ref,
                "doc_ids": docs,
                "targets": targets,
            }

        if len(doc_matches) > 1:
            return {
                "status": "multiple_docs",
                "fragment_ref": fragment_ref,
                "doc_ids": [doc_id for doc_id, _ in doc_matches],
                "targets": targets,
            }

        doc_id, target_hits = doc_matches[0]
        matched_lines = []
        for hits in target_hits.values():
            matched_lines.extend(hits)
        matched_lines = list({line["line_id"]: line for line in matched_lines}.values())

        candidate_words = []
        instance_type = instance.name.name_type.name if instance.name and instance.name.name_type else ""
        expected_keys = set()
        preferred_name = (instance.spelling or "").strip()
        if preferred_name:
            expected_keys.add(normalize_name_value(preferred_name))
        elif instance.name:
            expected_keys.add(normalize_name_value(instance.name.name))

        if instance.name:
            expected_keys.add(normalize_name_value(instance.name.query))
            expected_keys.update(
                normalize_name_value(part.strip())
                for part in re.split(r"[;,\\n]+", instance.name.variant_forms or "")
                if part.strip()
            )
            expected_keys.update(
                normalize_name_value(part.strip())
                for part in re.split(r"[;,\\n]+", instance.name.correspondence or "")
                if part.strip()
            )
        expected_keys = {key for key in expected_keys if key}

        for line in matched_lines:
            for word in self.load_words(line["line_id"]):
                if matches_name_type(instance_type, word["xml_content"], word["determinatives"]):
                    candidate = build_candidate_record(line, word, instance_type)
                    if candidate:
                        candidate_words.append(candidate)

        if not candidate_words and expected_keys:
            fallback_candidates = []
            for line in matched_lines:
                for word in self.load_words(line["line_id"]):
                    candidate = build_candidate_record(line, word, instance_type)
                    if not candidate:
                        continue
                    keys = candidate_name_keys(candidate, instance_type)
                    if score_candidate(expected_keys, keys) >= 0.75:
                        fallback_candidates.append(candidate)
            candidate_words = fallback_candidates

        if not candidate_words:
            return {
                "status": "no_name_token",
                "fragment_ref": fragment_ref,
                "doc_id": doc_id,
                "targets": targets,
                "matched_lines": matched_lines,
            }

        scored_candidates = []
        for candidate in candidate_words:
            keys = candidate_name_keys(candidate, instance_type)
            score = score_candidate(expected_keys, keys) if expected_keys else 0.0
            candidate["match_score"] = score
            scored_candidates.append(candidate)

        best_score = max((candidate["match_score"] for candidate in scored_candidates), default=0.0)
        best_candidates = [candidate for candidate in scored_candidates if candidate["match_score"] == best_score]
        unique_pairs = {
            (item["spelling"], item["determinative"])
            for item in best_candidates
        }

        if best_score < 0.75 or len(unique_pairs) != 1:
            return {
                "status": "ambiguous_token",
                "fragment_ref": fragment_ref,
                "doc_id": doc_id,
                "targets": targets,
                "matched_lines": matched_lines,
                "candidates": sorted(scored_candidates, key=lambda item: item["match_score"], reverse=True),
            }

        spelling, determinative = next(iter(unique_pairs))
        return {
            "status": "matched",
            "fragment_ref": fragment_ref,
            "doc_id": doc_id,
            "targets": targets,
            "matched_lines": matched_lines,
            "candidates": sorted(scored_candidates, key=lambda item: item["match_score"], reverse=True),
            "suggested_spelling": spelling,
            "suggested_determinative": determinative,
        }


class Command(BaseCommand):
    help = "Suggest or apply TLH-based spelling/determinative standardization for attestations."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Apply clean matches to the database.")
        parser.add_argument("--limit", type=int, default=None, help="Limit number of instances processed.")
        parser.add_argument("--instance-id", type=int, default=None, help="Process a single instance id.")
        parser.add_argument("--fragment", type=str, default=None, help="Process only one fragment reference.")
        parser.add_argument(
            "--report",
            type=str,
            default="tlh_spelling_report.csv",
            help="CSV report path.",
        )
        parser.add_argument(
            "--only-blank",
            action="store_true",
            help="Only process instances missing spelling or determinative.",
        )

    def handle(self, *args, **options):
        db_path = Path("TLH/hittite_corpus_v2.duckdb")
        if not db_path.exists():
            self.stderr.write(self.style.ERROR(f"Missing DuckDB file: {db_path}"))
            return

        matcher = TLHMatcher(db_path)
        det_lookup = {d.name: d for d in Determinative.objects.all()}

        qs = Instance.objects.select_related(
            "name",
            "name__name_type",
            "fragment",
            "fragment__series",
            "determinative",
        ).filter(fragment__series__name__in=SUPPORTED_SERIES)

        if options["instance_id"]:
            qs = qs.filter(pk=options["instance_id"])
        if options["fragment"]:
            qs = qs.filter(fragment__series_fragment=options["fragment"])

        instances = list(qs.order_by("id"))
        if options["only_blank"]:
            instances = [
                inst for inst in instances
                if not (inst.spelling and inst.spelling.strip()) or inst.determinative_variant_id is None
            ]
        if options["limit"]:
            instances = instances[: options["limit"]]

        report_rows = []
        applied = 0

        for instance in instances:
            result = matcher.match_instance(instance)
            suggested_spelling = result.get("suggested_spelling", "")
            suggested_det = result.get("suggested_determinative", "")
            canonical_suggested_det = Determinative.normalize_name(suggested_det)
            current_det = instance.display_determinative
            target_labels = "; ".join(
                target["label"] if isinstance(target, dict) else str(target)
                for target in result.get("targets", [])
            )
            matched_lines = "; ".join(
                f"{line['line_number_raw']} => {line['transliteration_plain'].strip()}"
                for line in result.get("matched_lines", [])
            )
            candidate_words = "; ".join(
                f"{cand['line_number_raw']}:{cand['raw_word']}[{cand['determinative']}]<{cand.get('match_score', 0):.2f}>"
                for cand in result.get("candidates", [])
            )

            row = {
                "instance_id": instance.id,
                "name": instance.name.name if instance.name else "",
                "name_type": instance.name.name_type.name if instance.name and instance.name.name_type else "",
                "fragment": instance.fragment.series_fragment if instance.fragment else "",
                "instance_line": instance.line or "",
                "status": result["status"],
                "doc_id": result.get("doc_id", ""),
                "targets": target_labels,
                "current_spelling": instance.spelling or "",
                "suggested_spelling": suggested_spelling,
                "current_determinative": current_det,
                "suggested_determinative": suggested_det,
                "matched_lines": matched_lines,
                "candidate_words": candidate_words,
            }
            report_rows.append(row)

            if not options["apply"] or result["status"] != "matched":
                continue

            changed = False
            if suggested_spelling and suggested_spelling != (instance.spelling or ""):
                instance.spelling = suggested_spelling
                changed = True
            if suggested_det or canonical_suggested_det:
                det_obj = None
                if canonical_suggested_det:
                    if canonical_suggested_det not in det_lookup:
                        det_lookup[canonical_suggested_det] = Determinative.objects.create(name=canonical_suggested_det)
                    det_obj = det_lookup[canonical_suggested_det]
                next_variant = DeterminativeVariant.get_or_create_for_value(
                    suggested_det or canonical_suggested_det,
                    determinative=det_obj,
                )
                if instance.determinative_variant_id != (next_variant.id if next_variant else None):
                    instance.determinative_variant = next_variant
                    changed = True
            if changed:
                instance.save(update_fields=["spelling", "determinative_variant"])
                applied += 1

        report_path = Path(options["report"])
        with report_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "instance_id",
                    "name",
                    "name_type",
                    "fragment",
                    "instance_line",
                    "status",
                    "doc_id",
                    "targets",
                    "current_spelling",
                    "suggested_spelling",
                    "current_determinative",
                    "suggested_determinative",
                    "matched_lines",
                    "candidate_words",
                ],
            )
            writer.writeheader()
            writer.writerows(report_rows)

        counts = defaultdict(int)
        for row in report_rows:
            counts[row["status"]] += 1

        self.stdout.write(self.style.SUCCESS(f"Wrote report to {report_path}"))
        for status in sorted(counts):
            self.stdout.write(f"{status}: {counts[status]}")
        if options["apply"]:
            self.stdout.write(self.style.SUCCESS(f"Applied updates to {applied} instances"))
