"""
Django management command to restore deleted instances from the original Excel file.

This can be used to restore instances that were deleted (e.g., during duplicate removal).
It imports instances by their original Instance_ID from the Excel file.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
import pandas as pd
from namefinder.models import (
    Instance, Name, Fragment, NameType, WritingType, 
    CompletenessType, Determinative
)


class Command(BaseCommand):
    help = 'Restore deleted instances from the original Excel file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--excel-file',
            type=str,
            default='Data Structure/instance.xlsx',
            help='Path to the instance Excel file'
        )
        parser.add_argument(
            '--instance-ids',
            type=str,
            help='Comma-separated list of Instance_IDs to restore'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be restored without actually restoring'
        )

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        instance_ids_str = options.get('instance_ids')
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        
        # Load Excel data
        self.stdout.write(f'Loading data from {excel_file}...')
        df = pd.read_excel(excel_file)
        self.stdout.write(f'Loaded {len(df)} rows')
        
        # Find instances that are missing from the database
        existing_original_ids = set(
            Instance.objects.filter(original_id__isnull=False)
            .values_list('original_id', flat=True)
        )
        
        all_excel_ids = set(df['Instance_ID'].dropna().astype(int))
        missing_ids = all_excel_ids - existing_original_ids
        
        self.stdout.write(f'Found {len(missing_ids)} instances in Excel that are not in database')
        
        if instance_ids_str:
            # Restore specific instances
            requested_ids = set(int(x.strip()) for x in instance_ids_str.split(','))
            restore_ids = requested_ids & missing_ids
            not_found = requested_ids - all_excel_ids
            already_exists = requested_ids - missing_ids - not_found
            
            if not_found:
                self.stdout.write(self.style.WARNING(f'IDs not found in Excel: {not_found}'))
            if already_exists:
                self.stdout.write(self.style.WARNING(f'IDs already in database: {already_exists}'))
        else:
            restore_ids = missing_ids
        
        if not restore_ids:
            self.stdout.write(self.style.SUCCESS('No instances to restore'))
            return
        
        self.stdout.write(f'Will restore {len(restore_ids)} instances')
        
        # Get rows to restore
        rows_to_restore = df[df['Instance_ID'].isin(restore_ids)]
        
        # Build caches for foreign keys
        name_map = {n.original_id: n for n in Name.objects.filter(original_id__isnull=False)}
        fragment_map = {f.original_id: f for f in Fragment.objects.filter(original_id__isnull=False)}
        type_cache = {t.name.lower(): t for t in NameType.objects.all()}
        writing_cache = {w.name.lower(): w for w in WritingType.objects.all()}
        completeness_cache = {c.name.lower(): c for c in CompletenessType.objects.all()}
        determinative_cache = {d.name: d for d in Determinative.objects.all()}
        
        restored = 0
        errors = 0
        
        with transaction.atomic():
            for _, row in rows_to_restore.iterrows():
                try:
                    original_id = int(row['Instance_ID'])
                    
                    # Get Name reference
                    name_id = int(row['Name_ID']) if pd.notna(row['Name_ID']) else None
                    name_obj = name_map.get(name_id) if name_id else None
                    
                    # Get Fragment reference  
                    fragment_id = int(row['Fragment_ID']) if pd.notna(row['Fragment_ID']) else None
                    fragment_obj = fragment_map.get(fragment_id) if fragment_id else None
                    
                    # Get Type
                    type_name = str(row['Type']).strip().lower() if pd.notna(row['Type']) else None
                    type_obj = type_cache.get(type_name) if type_name else None
                    
                    # Get Writing Type
                    writing_name = str(row['Writing']).strip().lower() if pd.notna(row['Writing']) else None
                    writing_obj = writing_cache.get(writing_name) if writing_name else None
                    
                    # Get Completeness
                    completeness_name = str(row['Completeness']).strip().lower() if pd.notna(row['Completeness']) else None
                    completeness_obj = completeness_cache.get(completeness_name) if completeness_name else None
                    
                    # Get Determinative
                    det_name = str(row['Determinative']).strip() if pd.notna(row['Determinative']) else None
                    det_obj = None
                    if det_name:
                        if det_name not in determinative_cache:
                            det_obj, _ = Determinative.objects.get_or_create(name=det_name)
                            determinative_cache[det_name] = det_obj
                        else:
                            det_obj = determinative_cache[det_name]
                    
                    # Get text fields
                    title_epithet = str(row['Title_Epithet']).strip() if pd.notna(row['Title_Epithet']) else None
                    spelling = str(row['Spelling']).strip() if pd.notna(row['Spelling']) else None
                    line = str(row['Line']).strip() if pd.notna(row['Line']) else None
                    notes = str(row['Notes']).strip() if pd.notna(row['Notes']) else None
                    
                    if not dry_run:
                        Instance.objects.create(
                            original_id=original_id,
                            name=name_obj,
                            fragment=fragment_obj,
                            title_epithet=title_epithet,
                            spelling=spelling,
                            instance_type=type_obj,
                            writing_type=writing_obj,
                            determinative=det_obj,
                            line=line,
                            completeness=completeness_obj,
                            notes=notes,
                        )
                    
                    restored += 1
                    
                except Exception as e:
                    self.stderr.write(f'Error restoring instance {original_id}: {e}')
                    errors += 1
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'Would restore {restored} instances'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Restored {restored} instances'))
        
        if errors:
            self.stdout.write(self.style.ERROR(f'Errors: {errors}'))
