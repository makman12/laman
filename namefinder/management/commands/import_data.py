"""
Django management command to import data from Excel files.
Imports fragments, names, and instances from the Data Structure folder.
"""
import os
from django.core.management.base import BaseCommand
from django.db import transaction
import pandas as pd
from namefinder.models import (
    NameType, WritingType, CompletenessType, PublicationType,
    Milieu, Series, Determinative, Fragment, Name, Instance
)


def safe_get(row, column, default=None):
    """Safely get a value from a pandas Series row"""
    try:
        if column in row.index:
            val = row[column]
            if pd.notna(val):
                return val
    except Exception:
        pass
    return default


class Command(BaseCommand):
    help = 'Import data from Excel files (fragment.xlsx, name.xlsx, instance.xlsx)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default='Data Structure',
            help='Directory containing the Excel files (default: "Data Structure")'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before import'
        )

    def handle(self, *args, **options):
        data_dir = options['data_dir']
        clear = options['clear']
        
        # Check if files exist
        fragment_file = os.path.join(data_dir, 'fragment.xlsx')
        name_file = os.path.join(data_dir, 'name.xlsx')
        instance_file = os.path.join(data_dir, 'instance.xlsx')
        
        for f in [fragment_file, name_file, instance_file]:
            if not os.path.exists(f):
                self.stderr.write(self.style.ERROR(f'File not found: {f}'))
                return
        
        if clear:
            self.stdout.write('Clearing existing data...')
            self.clear_data()
        
        # Import in order (lookup tables first, then main tables)
        with transaction.atomic():
            self.stdout.write('Step 1/6: Creating lookup tables...')
            self.create_lookup_tables()
            
            self.stdout.write('Step 2/6: Importing fragments...')
            fragment_map = self.import_fragments(fragment_file)
            
            self.stdout.write('Step 3/6: Importing names...')
            name_map = self.import_names(name_file)
            
            self.stdout.write('Step 4/6: Importing instances...')
            self.import_instances(instance_file, name_map, fragment_map)
            
            self.stdout.write('Step 5/6: Processing name determinatives...')
            self.process_name_determinatives(name_file)
            
            self.stdout.write('Step 6/6: Generating query fields...')
            self.generate_query_fields()
        
        self.stdout.write(self.style.SUCCESS('Import completed successfully!'))
        self.print_stats()

    def clear_data(self):
        """Clear all existing data"""
        Instance.objects.all().delete()
        Name.objects.all().delete()
        Fragment.objects.all().delete()
        Determinative.objects.all().delete()
        Series.objects.all().delete()
        Milieu.objects.all().delete()
        PublicationType.objects.all().delete()
        CompletenessType.objects.all().delete()
        WritingType.objects.all().delete()
        NameType.objects.all().delete()

    def create_lookup_tables(self):
        """Create predefined lookup table entries"""
        # Name Types
        for name in ['place', 'person', 'deity']:
            NameType.objects.get_or_create(name=name)
        
        # Writing Types
        for name in ['phonetic', 'logographic', 'hieroglyphic', 'akkadographic']:
            WritingType.objects.get_or_create(name=name)
        
        # Completeness Types
        for name in ['complete', 'incomplete', 'acephalous']:
            CompletenessType.objects.get_or_create(name=name)
        
        # Publication Types
        for name in ['Publication', 'Other', 'Inventory']:
            PublicationType.objects.get_or_create(name=name)
        
        # Milieu - will be populated from data
        
        self.stdout.write(f'  Created {NameType.objects.count()} name types')
        self.stdout.write(f'  Created {WritingType.objects.count()} writing types')
        self.stdout.write(f'  Created {CompletenessType.objects.count()} completeness types')
        self.stdout.write(f'  Created {PublicationType.objects.count()} publication types')

    def import_fragments(self, filepath):
        """Import fragments from Excel file"""
        df = pd.read_excel(filepath)
        self.stdout.write(f'  Read {len(df)} rows from {filepath}')
        
        fragment_map = {}  # Maps original Fragment_ID to new Fragment object
        series_cache = {}
        pub_type_cache = {}
        
        for _, row in df.iterrows():
            series_name = str(row['Series']).strip() if pd.notna(row['Series']) else None
            fragment_num = str(row['Fragment']).strip() if pd.notna(row['Fragment']) else ''
            series_fragment = str(row['Series_Fragment']).strip() if pd.notna(row['Series_Fragment']) else ''
            original_id = int(row['Fragment_ID'])
            pub_type_name = str(row['Publication']).strip() if pd.notna(row['Publication']) else None
            
            # Get or create Series
            if series_name:
                if series_name not in series_cache:
                    series_obj, _ = Series.objects.get_or_create(name=series_name)
                    series_cache[series_name] = series_obj
                series_obj = series_cache[series_name]
            else:
                continue  # Skip if no series
            
            # Get Publication Type
            pub_type_obj = None
            if pub_type_name:
                if pub_type_name not in pub_type_cache:
                    pub_type_obj, _ = PublicationType.objects.get_or_create(name=pub_type_name)
                    pub_type_cache[pub_type_name] = pub_type_obj
                pub_type_obj = pub_type_cache[pub_type_name]
            
            # Create Fragment
            fragment, created = Fragment.objects.update_or_create(
                original_id=original_id,
                defaults={
                    'series': series_obj,
                    'fragment_number': fragment_num,
                    'series_fragment': series_fragment,
                    'publication_type': pub_type_obj,
                }
            )
            fragment_map[original_id] = fragment
        
        self.stdout.write(f'  Imported {len(fragment_map)} fragments')
        self.stdout.write(f'  Created {Series.objects.count()} series')
        return fragment_map

    def import_names(self, filepath):
        """Import names from Excel file"""
        df = pd.read_excel(filepath)
        self.stdout.write(f'  Read {len(df)} rows from {filepath}')
        
        name_map = {}  # Maps original Name_ID to new Name object
        type_cache = {}
        writing_cache = {}
        completeness_cache = {}
        milieu_cache = {}
        
        for _, row in df.iterrows():
            original_id = int(row['Name_ID'])
            name_text = str(row['Name']).strip() if pd.notna(row['Name']) else ''
            
            # Get Type
            type_obj = None
            type_name = str(row['Type']).strip().lower() if pd.notna(row['Type']) else None
            if type_name:
                if type_name not in type_cache:
                    type_obj, _ = NameType.objects.get_or_create(name=type_name)
                    type_cache[type_name] = type_obj
                type_obj = type_cache[type_name]
            
            # Get Writing Type
            writing_obj = None
            writing_name = str(row['Writing']).strip().lower() if pd.notna(row['Writing']) else None
            if writing_name:
                if writing_name not in writing_cache:
                    writing_obj, _ = WritingType.objects.get_or_create(name=writing_name)
                    writing_cache[writing_name] = writing_obj
                writing_obj = writing_cache[writing_name]
            
            # Get Completeness
            completeness_obj = None
            completeness_name = str(row['Completeness']).strip().lower() if pd.notna(row['Completeness']) else None
            if completeness_name:
                if completeness_name not in completeness_cache:
                    completeness_obj, _ = CompletenessType.objects.get_or_create(name=completeness_name)
                    completeness_cache[completeness_name] = completeness_obj
                completeness_obj = completeness_cache[completeness_name]
            
            # Get Milieu
            milieu_obj = None
            milieu_name = str(row['Milieu']).strip() if pd.notna(row['Milieu']) else None
            if milieu_name:
                if milieu_name not in milieu_cache:
                    milieu_obj, _ = Milieu.objects.get_or_create(name=milieu_name)
                    milieu_cache[milieu_name] = milieu_obj
                milieu_obj = milieu_cache[milieu_name]
            
            # Handle optional fields - use direct column access with pd.notna check
            variant_forms = str(row['Variant_Forms']).strip() if 'Variant_Forms' in row.index and pd.notna(row['Variant_Forms']) else None
            correspondence = str(row['Correspondence']).strip() if 'Correspondence' in row.index and pd.notna(row['Correspondence']) else None
            literature = str(row['Literature']).strip() if 'Literature' in row.index and pd.notna(row['Literature']) else None
            query = str(row['Query']).strip() if 'Query' in row.index and pd.notna(row['Query']) else None
            uncertain = bool(row['Uncertain']) if 'Uncertain' in row.index and pd.notna(row['Uncertain']) else False
            
            # Create Name
            name_obj, created = Name.objects.update_or_create(
                original_id=original_id,
                defaults={
                    'name': name_text,
                    'name_type': type_obj,
                    'writing_type': writing_obj,
                    'completeness': completeness_obj,
                    'milieu': milieu_obj,
                    'variant_forms': variant_forms,
                    'correspondence': correspondence,
                    'literature': literature,
                    'query': query,
                    'uncertain': uncertain,
                }
            )
            name_map[original_id] = name_obj
        
        self.stdout.write(f'  Imported {len(name_map)} names')
        self.stdout.write(f'  Created {Milieu.objects.count()} milieus')
        return name_map

    def import_instances(self, filepath, name_map, fragment_map):
        """Import instances from Excel file"""
        df = pd.read_excel(filepath)
        self.stdout.write(f'  Read {len(df)} rows from {filepath}')
        
        type_cache = {}
        writing_cache = {}
        completeness_cache = {}
        determinative_cache = {}
        
        instances_created = 0
        instances_skipped = 0
        
        for _, row in df.iterrows():
            original_id = int(row['Instance_ID'])
            
            # Get Name reference
            name_id = safe_get(row, 'Name_ID')
            name_obj = None
            if name_id is not None:
                name_id = int(name_id)
                name_obj = name_map.get(name_id)
            
            # Get Fragment reference
            fragment_id = safe_get(row, 'Fragment_ID')
            fragment_obj = None
            if fragment_id is not None:
                fragment_id = int(fragment_id)
                fragment_obj = fragment_map.get(fragment_id)
            
            # Get Type
            type_obj = None
            type_val = safe_get(row, 'Type')
            type_name = str(type_val).strip().lower() if type_val else None
            if type_name:
                if type_name not in type_cache:
                    type_obj, _ = NameType.objects.get_or_create(name=type_name)
                    type_cache[type_name] = type_obj
                type_obj = type_cache[type_name]
            
            # Get Writing Type
            writing_obj = None
            writing_val = safe_get(row, 'Writing')
            writing_name = str(writing_val).strip().lower() if writing_val else None
            if writing_name:
                if writing_name not in writing_cache:
                    writing_obj, _ = WritingType.objects.get_or_create(name=writing_name)
                    writing_cache[writing_name] = writing_obj
                writing_obj = writing_cache[writing_name]
            
            # Get Completeness
            completeness_obj = None
            completeness_val = safe_get(row, 'Completeness')
            completeness_name = str(completeness_val).strip().lower() if completeness_val else None
            if completeness_name:
                if completeness_name not in completeness_cache:
                    completeness_obj, _ = CompletenessType.objects.get_or_create(name=completeness_name)
                    completeness_cache[completeness_name] = completeness_obj
                completeness_obj = completeness_cache[completeness_name]
            
            # Get Determinative
            determinative_obj = None
            det_val = safe_get(row, 'Determinative')
            determinative_name = str(det_val).strip() if det_val else None
            if determinative_name:
                if determinative_name not in determinative_cache:
                    determinative_obj, _ = Determinative.objects.get_or_create(name=determinative_name)
                    determinative_cache[determinative_name] = determinative_obj
                determinative_obj = determinative_cache[determinative_name]
            
            # Handle optional fields
            title_val = safe_get(row, 'Title_Epithet')
            title_epithet = str(title_val).strip() if title_val else None
            spelling_val = safe_get(row, 'Spelling')
            spelling = str(spelling_val).strip() if spelling_val else None
            line_val = safe_get(row, 'Line')
            line = str(line_val).strip() if line_val else None
            notes_val = safe_get(row, 'Notes')
            notes = str(notes_val).strip() if notes_val else None
            
            # Create Instance
            try:
                instance, created = Instance.objects.update_or_create(
                    original_id=original_id,
                    defaults={
                        'name': name_obj,
                        'fragment': fragment_obj,
                        'title_epithet': title_epithet,
                        'spelling': spelling,
                        'instance_type': type_obj,
                        'writing_type': writing_obj,
                        'determinative': determinative_obj,
                        'line': line,
                        'completeness': completeness_obj,
                        'notes': notes,
                    }
                )
                instances_created += 1
            except Exception as e:
                self.stderr.write(f'  Error importing instance {original_id}: {e}')
                instances_skipped += 1
        
        self.stdout.write(f'  Imported {instances_created} instances')
        if instances_skipped:
            self.stdout.write(self.style.WARNING(f'  Skipped {instances_skipped} instances due to errors'))
        self.stdout.write(f'  Created {Determinative.objects.count()} determinatives')

    def process_name_determinatives(self, filepath):
        """Process the comma-separated determinatives in name.xlsx and create M2M relationships"""
        df = pd.read_excel(filepath)
        
        determinative_cache = {}
        count = 0
        
        for _, row in df.iterrows():
            original_id = int(row['Name_ID'])
            determinative_str = str(row['Determinative']).strip() if pd.notna(row.get('Determinative')) else None
            
            if not determinative_str:
                continue
            
            try:
                name_obj = Name.objects.get(original_id=original_id)
            except Name.DoesNotExist:
                continue
            
            # Split comma-separated determinatives
            determinatives = [d.strip() for d in determinative_str.split(',') if d.strip()]
            
            for det_name in determinatives:
                if det_name not in determinative_cache:
                    det_obj, _ = Determinative.objects.get_or_create(name=det_name)
                    determinative_cache[det_name] = det_obj
                det_obj = determinative_cache[det_name]
                name_obj.determinatives.add(det_obj)
                count += 1
        
        self.stdout.write(f'  Created {count} name-determinative relationships')

    def generate_query_fields(self):
        """Generate query fields for names that don't have them"""
        names_without_query = Name.objects.filter(query__isnull=True) | Name.objects.filter(query='')
        count = 0
        
        for name_obj in names_without_query:
            if name_obj.name:
                name_obj.query = Name.normalize_for_search(name_obj.name)
                name_obj.save(update_fields=['query'])
                count += 1
        
        self.stdout.write(f'  Generated query fields for {count} names')

    def print_stats(self):
        """Print final statistics"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Final Statistics:')
        self.stdout.write('='*50)
        self.stdout.write(f'  Name Types: {NameType.objects.count()}')
        self.stdout.write(f'  Writing Types: {WritingType.objects.count()}')
        self.stdout.write(f'  Completeness Types: {CompletenessType.objects.count()}')
        self.stdout.write(f'  Publication Types: {PublicationType.objects.count()}')
        self.stdout.write(f'  Milieus: {Milieu.objects.count()}')
        self.stdout.write(f'  Series: {Series.objects.count()}')
        self.stdout.write(f'  Determinatives: {Determinative.objects.count()}')
        self.stdout.write(f'  Fragments: {Fragment.objects.count()}')
        self.stdout.write(f'  Names: {Name.objects.count()}')
        self.stdout.write(f'  Instances: {Instance.objects.count()}')
        self.stdout.write('='*50)
