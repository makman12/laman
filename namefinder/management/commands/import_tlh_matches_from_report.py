import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand

from namefinder.models import Instance, InstanceTLHMatch


def parse_targets(value):
    if not value:
        return []
    return [{"label": part.strip()} for part in value.split("; ") if part.strip()]


def parse_matched_lines(value):
    if not value:
        return []
    lines = []
    for part in value.split("; "):
        if not part.strip():
            continue
        if " => " in part:
            line_number_raw, transliteration_plain = part.split(" => ", 1)
        else:
            line_number_raw, transliteration_plain = part, ""
        lines.append(
            {
                "line_number_raw": line_number_raw.strip(),
                "transliteration_plain": transliteration_plain.strip(),
            }
        )
    return lines


def parse_candidates(value):
    if not value:
        return []
    candidates = []
    pattern = re.compile(r"^(?P<line>.*?):(?P<raw>.*?)\[(?P<det>.*?)\]<(?P<score>[0-9.]+)>$")
    for part in value.split("; "):
        part = part.strip()
        if not part:
            continue
        match = pattern.match(part)
        if match:
            candidates.append(
                {
                    "line_number_raw": match.group("line").strip(),
                    "raw_word": match.group("raw").strip(),
                    "determinative": match.group("det").strip(),
                    "match_score": float(match.group("score")),
                }
            )
        else:
            candidates.append(
                {
                    "line_number_raw": "",
                    "raw_word": part,
                    "determinative": "",
                    "match_score": 0.0,
                }
            )
    return candidates


class Command(BaseCommand):
    help = "Import persisted TLH match rows from an existing CSV report into SQLite."

    def add_arguments(self, parser):
        parser.add_argument(
            "--report",
            type=str,
            default="tlh_attestation_match_report_v10.csv",
            help="CSV report to import.",
        )

    def handle(self, *args, **options):
        report_path = Path(options["report"])
        if not report_path.exists():
            self.stderr.write(self.style.ERROR(f"Missing report file: {report_path}"))
            return

        rows = list(csv.DictReader(report_path.open(encoding="utf-8-sig")))
        instance_ids = [int(row["instance_id"]) for row in rows if row.get("instance_id")]
        existing_ids = set(Instance.objects.filter(id__in=instance_ids).values_list("id", flat=True))

        records = []
        skipped = 0
        for row in rows:
            if not row.get("instance_id"):
                skipped += 1
                continue
            instance_id = int(row["instance_id"])
            if instance_id not in existing_ids:
                skipped += 1
                continue
            records.append(
                InstanceTLHMatch(
                    instance_id=instance_id,
                    status=row.get("status", "") or "no_doc",
                    doc_id=row.get("doc_id", "") or "",
                    suggested_spelling=row.get("suggested_spelling", "") or "",
                    suggested_determinative=row.get("suggested_determinative", "") or "",
                    targets=parse_targets(row.get("targets", "")),
                    matched_lines=parse_matched_lines(row.get("matched_lines", "")),
                    candidates=parse_candidates(row.get("candidate_words", "")),
                    extra_data={
                        "fragment": row.get("fragment", "") or "",
                        "instance_line": row.get("instance_line", "") or "",
                        "name": row.get("name", "") or "",
                        "name_type": row.get("name_type", "") or "",
                        "current_spelling": row.get("current_spelling", "") or "",
                        "current_determinative": row.get("current_determinative", "") or "",
                    },
                )
            )

        InstanceTLHMatch.objects.bulk_create(
            records,
            batch_size=500,
            update_conflicts=True,
            unique_fields=["instance"],
            update_fields=[
                "status",
                "doc_id",
                "suggested_spelling",
                "suggested_determinative",
                "targets",
                "matched_lines",
                "candidates",
                "extra_data",
                "updated_at",
            ],
        )

        self.stdout.write(self.style.SUCCESS(f"Imported {len(records)} TLH match rows from {report_path}"))
        if skipped:
            self.stdout.write(f"Skipped {skipped} rows with missing instances or ids")
