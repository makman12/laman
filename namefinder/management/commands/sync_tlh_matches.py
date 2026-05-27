from pathlib import Path

from django.core.management.base import BaseCommand

from namefinder.management.commands.tlh_standardize_attestations import SUPPORTED_SERIES, TLHMatcher
from namefinder.models import Instance, InstanceTLHMatch


class Command(BaseCommand):
    help = "Persist TLH matching results into the SQLite database for attestation browsing."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Limit number of instances processed.")
        parser.add_argument("--instance-id", type=int, default=None, help="Process a single instance id.")
        parser.add_argument("--fragment", type=str, default=None, help="Process only one fragment reference.")
        parser.add_argument("--only-missing", action="store_true", help="Only process instances without a saved TLH match row.")

    def handle(self, *args, **options):
        db_path = Path("TLH/hittite_corpus_v2.duckdb")
        if not db_path.exists():
            self.stderr.write(self.style.ERROR(f"Missing DuckDB file: {db_path}"))
            return

        matcher = TLHMatcher(db_path)
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
        if options["only_missing"]:
            qs = qs.filter(tlh_match_record__isnull=True)

        instances = list(qs.order_by("id"))
        if options["limit"]:
            instances = instances[: options["limit"]]

        saved = 0
        counts = {}

        for instance in instances:
            result = matcher.match_instance(instance)
            InstanceTLHMatch.objects.update_or_create(
                instance=instance,
                defaults={
                    "status": result["status"],
                    "doc_id": result.get("doc_id", ""),
                    "suggested_spelling": result.get("suggested_spelling", ""),
                    "suggested_determinative": result.get("suggested_determinative", ""),
                    "targets": result.get("targets", []),
                    "matched_lines": result.get("matched_lines", []),
                    "candidates": result.get("candidates", []),
                    "extra_data": {
                        "fragment_ref": result.get("fragment_ref", ""),
                        "doc_ids": result.get("doc_ids", []),
                    },
                },
            )
            counts[result["status"]] = counts.get(result["status"], 0) + 1
            saved += 1

        self.stdout.write(self.style.SUCCESS(f"Saved TLH matches for {saved} attestations"))
        for status in sorted(counts):
            self.stdout.write(f"{status}: {counts[status]}")
