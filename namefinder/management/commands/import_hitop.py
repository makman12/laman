"""
Import place name attestations from HiTop Excel file.

Usage: python manage.py import_hitop
"""
import re
import pandas as pd
from django.core.management.base import BaseCommand
from namefinder.models import (
    Name, Instance, Fragment, NameType, Determinative, DeterminativeVariant
)


def is_fragmentary(name):
    """Check if a name is fragmentary/incomplete."""
    if not name:
        return False
    return bool(
        '[' in name or ']' in name or '…' in name or '?' in name or
        name.endswith('-') or name.endswith('–') or 'x' in name
    )


def normalize_inv(inv):
    """Normalize inventory number for matching: strip +/(+) prefixes, collapse spaces."""
    if not inv or pd.isna(inv):
        return ''
    inv = str(inv).strip()
    # Strip leading (+) or +
    inv = re.sub(r'^\(\+\)\s*', '', inv)
    inv = re.sub(r'^\+\s*', '', inv)
    # Collapse multiple spaces
    inv = re.sub(r'\s+', ' ', inv)
    return inv


class Command(BaseCommand):
    help = 'Import place name attestations from HiTop Excel file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be imported without making changes'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        xlsx_path = 'legacyData/HiTop28.04.2023b.xlsx'

        self.stdout.write(f'Reading {xlsx_path}...')
        df = pd.read_excel(xlsx_path)
        self.stdout.write(f'Loaded {len(df)} rows')

        # Skip rows with neither publ nor inv
        df_importable = df[df['publ'].notna() | df['inv'].notna()].copy()
        skipped_no_ref = len(df) - len(df_importable)
        self.stdout.write(f'Skipped {skipped_no_ref} rows with no publ or inv')
        self.stdout.write(f'Importable rows: {len(df_importable)}')

        # Strip whitespace from publ
        df_importable.loc[:, 'publ'] = df_importable['publ'].apply(
            lambda x: str(x).strip() if pd.notna(x) else None
        )

        # Build caches
        place_type = NameType.objects.get(name='place')

        self.stdout.write('Building name cache...')
        name_cache = {}
        for n in Name.objects.filter(name_type=place_type):
            name_cache[n.name] = n

        self.stdout.write('Building fragment cache...')
        fragment_cache = {}
        for f in Fragment.objects.all():
            fragment_cache[f.series_fragment] = f

        self.stdout.write('Building inventory cache...')
        inv_cache = {}
        for f in Fragment.objects.exclude(inventory_number__isnull=True).exclude(inventory_number=''):
            # Store both raw and normalized
            inv_cache[f.inventory_number] = f
            normalized = normalize_inv(f.inventory_number)
            if normalized and normalized != f.inventory_number:
                inv_cache[normalized] = f

        self.stdout.write('Building determinative cache...')
        det_cache = {}
        for d in Determinative.objects.all():
            det_cache[d.name] = d

        # Step 1: Create new Name records
        hitop_names = set(df_importable['Name'].dropna().unique())
        new_names = hitop_names - set(name_cache.keys())
        names_created = 0

        if new_names:
            self.stdout.write(f'Creating {len(new_names)} new place names...')
            for name_str in sorted(new_names):
                if dry_run:
                    self.stdout.write(f'  [DRY RUN] Would create: {name_str}')
                else:
                    n = Name(
                        name=name_str,
                        name_type=place_type,
                        is_fragmentary=is_fragmentary(name_str),
                    )
                    n.save()  # triggers query field normalization
                    name_cache[name_str] = n
                    names_created += 1

        # Step 2: Create Instance records
        instances_to_create = []
        unmatched_names = set()
        unmatched_fragments = {}  # fragment_ref -> count
        matched_publ = 0
        matched_inv = 0

        for idx, row in df_importable.iterrows():
            name_str = row['Name'] if pd.notna(row.get('Name')) else None
            publ = row['publ'] if pd.notna(row.get('publ')) else None
            inv = row['inv'] if pd.notna(row.get('inv')) else None
            stelle = str(row['stelle']).strip() if pd.notna(row.get('stelle')) else ''
            translit = str(row['translit']).strip() if pd.notna(row.get('translit')) else None
            geo_ident = str(row['geogr. ident.']).strip() if pd.notna(row.get('geogr. ident.')) else None
            anmerk = str(row['anmerk']).strip() if pd.notna(row.get('anmerk')) else ''
            gramm = str(row['gramm']).strip() if pd.notna(row.get('gramm')) else ''

            # Match name
            if not name_str or name_str not in name_cache:
                if name_str:
                    unmatched_names.add(name_str)
                continue
            name_obj = name_cache[name_str]

            # Match fragment - Tier 1: publ
            fragment_obj = None
            if publ:
                fragment_obj = fragment_cache.get(publ)
                if fragment_obj:
                    matched_publ += 1

            # Tier 2: inv
            if not fragment_obj and inv:
                inv_str = str(inv).strip()
                # Try exact match
                fragment_obj = inv_cache.get(inv_str)
                if not fragment_obj:
                    # Try normalized
                    norm = normalize_inv(inv_str)
                    fragment_obj = inv_cache.get(norm)
                if not fragment_obj:
                    # Fallback: icontains query
                    norm = normalize_inv(inv_str)
                    if norm:
                        matches = Fragment.objects.filter(inventory_number__icontains=norm)
                        if matches.count() == 1:
                            fragment_obj = matches.first()
                            inv_cache[inv_str] = fragment_obj
                if fragment_obj:
                    matched_inv += 1

            if not fragment_obj:
                ref = publ or inv or '(none)'
                unmatched_fragments[ref] = unmatched_fragments.get(ref, 0) + 1
                continue

            # Extract line from stelle
            if publ and stelle.startswith(publ):
                line = stelle[len(publ):].strip()
            else:
                line = stelle

            # Determinative
            det_obj = None
            det_variant = None
            if geo_ident and geo_ident != 'nan':
                canonical_geo_ident = Determinative.normalize_name(geo_ident)
                if canonical_geo_ident and canonical_geo_ident not in det_cache:
                    if not dry_run:
                        det_obj = Determinative.objects.create(name=canonical_geo_ident)
                        det_cache[canonical_geo_ident] = det_obj
                else:
                    det_obj = det_cache.get(canonical_geo_ident)
                cleaned_geo_ident = Determinative.clean_variant_value(geo_ident)
                if cleaned_geo_ident and not dry_run:
                    det_variant = DeterminativeVariant.get_or_create_for_value(
                        cleaned_geo_ident,
                        determinative=det_obj,
                    )

            # Notes: combine anmerk + gramm
            notes_parts = []
            if anmerk and anmerk != 'nan':
                notes_parts.append(anmerk)
            if gramm and gramm != 'nan':
                notes_parts.append(gramm)
            notes = '; '.join(notes_parts) if notes_parts else None

            instances_to_create.append(Instance(
                name=name_obj,
                fragment=fragment_obj,
                line=line or None,
                spelling=translit if translit and translit != 'nan' else None,
                instance_type=place_type,
                determinative_variant=det_variant,
                notes=notes,
            ))

        # Bulk create
        if dry_run:
            self.stdout.write(f'\n[DRY RUN] Would create {len(instances_to_create)} instances')
        else:
            Instance.objects.bulk_create(instances_to_create, batch_size=1000)

        # Report
        self.stdout.write(self.style.SUCCESS(f'\n=== Import Results ==='))
        self.stdout.write(f'Names created: {names_created}')
        self.stdout.write(f'Instances created: {len(instances_to_create)}')
        self.stdout.write(f'  - Matched via publ: {matched_publ}')
        self.stdout.write(f'  - Matched via inv: {matched_inv}')
        self.stdout.write(f'Rows skipped (no ref): {skipped_no_ref}')

        if unmatched_names:
            self.stdout.write(self.style.WARNING(
                f'\nUnmatched names ({len(unmatched_names)}):'))
            for n in sorted(unmatched_names):
                self.stdout.write(f'  {n}')

        if unmatched_fragments:
            total_unmatched = sum(unmatched_fragments.values())
            self.stdout.write(self.style.WARNING(
                f'\nUnmatched fragments ({len(unmatched_fragments)} unique, {total_unmatched} rows):'))
            for ref, count in sorted(unmatched_fragments.items()):
                self.stdout.write(f'  {ref} ({count} rows)')
