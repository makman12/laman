"""
Django management command to remove duplicate instances.

Duplicates are identified by matching (name_id, fragment_id, line, spelling).
When duplicates are found, the first instance (lowest ID) is kept and others are deleted.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from collections import defaultdict
from namefinder.models import Instance


class Command(BaseCommand):
    help = 'Remove duplicate instances based on (name, fragment, line, spelling)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--name-id',
            type=int,
            help='Only check instances for a specific Name ID'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        name_id_filter = options.get('name_id')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        
        # Query instances
        instances_qs = Instance.objects.all().select_related('name', 'fragment')
        if name_id_filter:
            instances_qs = instances_qs.filter(name_id=name_id_filter)
        
        self.stdout.write(f'Checking {instances_qs.count()} instances for duplicates...')
        
        # Group by (name_id, fragment_id, line, spelling)
        groups = defaultdict(list)
        for inst in instances_qs:
            key = (inst.name_id, inst.fragment_id, inst.line, inst.spelling)
            groups[key].append(inst)
        
        # Find duplicates (groups with more than 1 instance)
        duplicates = {k: v for k, v in groups.items() if len(v) > 1}
        
        if not duplicates:
            self.stdout.write(self.style.SUCCESS('No duplicates found!'))
            return
        
        total_groups = len(duplicates)
        total_to_delete = sum(len(v) - 1 for v in duplicates.values())
        
        self.stdout.write(f'Found {total_groups} groups with duplicates')
        self.stdout.write(f'Total duplicate instances to remove: {total_to_delete}')
        
        # Collect IDs to delete (keep the one with lowest ID in each group)
        ids_to_delete = []
        
        for (name_id, fragment_id, line, spelling), instances in duplicates.items():
            # Sort by ID to keep the lowest (oldest) one
            sorted_instances = sorted(instances, key=lambda x: x.pk)
            keep = sorted_instances[0]
            delete = sorted_instances[1:]
            
            ids_to_delete.extend([inst.pk for inst in delete])
            
            # Show what we're doing (first few only)
            if len(ids_to_delete) <= 20:
                name_str = keep.name.name if keep.name else "Unknown"
                frag_str = keep.fragment.series_fragment if keep.fragment else "Unknown"
                self.stdout.write(
                    f'  Keep ID {keep.pk}, delete {[inst.pk for inst in delete]} '
                    f'({name_str} in {frag_str}, line {line})'
                )
        
        if len(ids_to_delete) > 20:
            self.stdout.write(f'  ... and {len(ids_to_delete) - 20} more')
        
        # Delete duplicates
        if not dry_run:
            with transaction.atomic():
                deleted_count, _ = Instance.objects.filter(pk__in=ids_to_delete).delete()
                self.stdout.write(self.style.SUCCESS(f'\nDeleted {deleted_count} duplicate instances'))
        else:
            self.stdout.write(self.style.WARNING(f'\nWould delete {len(ids_to_delete)} duplicate instances'))
        
        # Summary by name
        self.stdout.write('\nDuplicates by Name (top 10):')
        name_dup_counts = defaultdict(int)
        for (name_id, frag_id, line, spelling), insts in duplicates.items():
            name_dup_counts[name_id] += len(insts) - 1
        
        sorted_names = sorted(name_dup_counts.items(), key=lambda x: -x[1])[:10]
        from namefinder.models import Name
        for name_id, count in sorted_names:
            try:
                name = Name.objects.get(pk=name_id)
                self.stdout.write(f'  {name.name} ({name.name_type}): {count} duplicates')
            except Name.DoesNotExist:
                self.stdout.write(f'  Name ID {name_id}: {count} duplicates')
