import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand

from namefinder.models import Instance


NOISY_TOKENS = ("seal", "twice", "due volte")


def normalize_spacing(value):
    value = value.replace("’", "′").replace("'", "′")
    value = re.sub(r"\s+", " ", value.strip())
    value = value.replace("obv,", "obv.").replace("rev,", "rev.")
    value = value.replace("obv.!","obv.").replace("rev.!","rev.")
    value = value.replace("obv.?","obv.").replace("rev.?","rev.")
    value = value.replace("vs.?","vs.").replace("rs.?","rs.")
    value = value.replace("II?", "II").replace("III?", "III").replace("IV?", "IV").replace("V?", "V").replace("VI?", "VI").replace("I?", "I")
    value = value.replace("l.col.", "l. col. ").replace("r.col.", "r. col. ")
    value = value.replace("l.col", "l. col").replace("r.col", "r. col")
    value = value.replace("lo.e.", "l.e.").replace("ro.e.", "r.e.").replace("Ru.e.", "r.e.")
    value = value.replace("m 12", "12")
    value = value.replace(",,", ",")
    return value


def extract_prefix(segment):
    segment = normalize_spacing(segment)
    segment = re.sub(r"^[\[\]]+", "", segment).strip()
    match = re.match(
        r"^(?P<prefix>(?:(?:obv\.?|rev\.?|vs\.?|rs\.?|u\.e\.?|l\.e\.?|r\.e\.?|lo\.e\.?|ro\.e\.?|col\.?|l\.\s*col\.?|r\.\s*col\.?)\s*)?(?:(?:[ivx]+)\b\s*)?)",
        segment,
        re.IGNORECASE,
    )
    prefix = (match.group("prefix") or "").strip()
    rest = segment[len(prefix):].strip()
    return prefix, rest


def looks_like_line_body(value):
    value = value.strip()
    return bool(re.match(r"^\d+[^\n,]*$", value))


def split_compact_commas(raw_line):
    raw_line = normalize_spacing(raw_line)
    compact = re.sub(r"\s*,\s*", ", ", raw_line)
    compact = re.sub(r"(?<=\d),(?=\d)", ", ", compact)
    return compact


def split_line_references(raw_line):
    raw_line = split_compact_commas(raw_line or "")
    if "," not in raw_line:
        return None, "no_comma"
    if any(token in raw_line.lower() for token in NOISY_TOKENS):
        return None, "contains_note"

    segments = [seg.strip() for seg in raw_line.split(",") if seg.strip()]
    if len(segments) < 2:
        return None, "too_few_segments"

    results = []
    current_prefix = ""

    for segment in segments:
        segment = re.sub(r"^\[(.*)\]$", r"\1", segment).strip()
        prefix, rest = extract_prefix(segment)

        if prefix and looks_like_line_body(rest):
            current_prefix = prefix
            combined = f"{prefix} {rest}".strip()
            results.append(normalize_spacing(combined))
            continue

        if looks_like_line_body(segment):
            if current_prefix:
                results.append(normalize_spacing(f"{current_prefix} {segment}"))
            else:
                results.append(normalize_spacing(segment))
            continue

        return None, "unparsed_segment"

    deduped = []
    seen = set()
    for value in results:
        if value not in seen:
            seen.add(value)
            deduped.append(value)

    return deduped if len(deduped) > 1 else None, "single_result"


class Command(BaseCommand):
    help = "Split bundled attestation lines like 'obv. i 23, 32' into separate Instance rows."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Apply clean splits to the database.")
        parser.add_argument("--instance-id", type=int, default=None, help="Process a single instance.")
        parser.add_argument("--limit", type=int, default=None, help="Limit number of instances processed.")
        parser.add_argument(
            "--report",
            type=str,
            default="split_multiline_instances_report.csv",
            help="CSV report path.",
        )

    def handle(self, *args, **options):
        qs = Instance.objects.select_related("name", "fragment").filter(line__contains=",").order_by("id")
        if options["instance_id"]:
            qs = qs.filter(pk=options["instance_id"])

        instances = list(qs)
        if options["limit"]:
            instances = instances[: options["limit"]]

        report_rows = []
        split_count = 0
        new_count = 0

        for inst in instances:
            split_lines, status = split_line_references(inst.line)
            row = {
                "instance_id": inst.id,
                "name": inst.name.name if inst.name else "",
                "fragment": inst.fragment.series_fragment if inst.fragment else "",
                "original_line": inst.line or "",
                "status": "splittable" if split_lines else status,
                "split_lines": "; ".join(split_lines or []),
            }
            report_rows.append(row)

            if not options["apply"] or not split_lines:
                continue

            inst.line = split_lines[0]
            inst.save(update_fields=["line"])
            split_count += 1

            for extra_line in split_lines[1:]:
                exists = Instance.objects.filter(
                    name_id=inst.name_id,
                    fragment_id=inst.fragment_id,
                    line=extra_line,
                    spelling=inst.spelling,
                ).exists()
                if exists:
                    continue

                Instance.objects.create(
                    name_id=inst.name_id,
                    fragment_id=inst.fragment_id,
                    title_epithet=inst.title_epithet,
                    spelling=inst.spelling,
                    instance_type_id=inst.instance_type_id,
                    writing_type_id=inst.writing_type_id,
                    determinative_variant_id=inst.determinative_variant_id,
                    line=extra_line,
                    completeness_id=inst.completeness_id,
                    notes=inst.notes,
                )
                new_count += 1

        report_path = Path(options["report"])
        with report_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "instance_id",
                    "name",
                    "fragment",
                    "original_line",
                    "status",
                    "split_lines",
                ],
            )
            writer.writeheader()
            writer.writerows(report_rows)

        self.stdout.write(self.style.SUCCESS(f"Wrote report to {report_path}"))
        self.stdout.write(f"Processed {len(report_rows)} instances")
        if options["apply"]:
            self.stdout.write(self.style.SUCCESS(f"Updated originals: {split_count}"))
            self.stdout.write(self.style.SUCCESS(f"Created new instances: {new_count}"))
