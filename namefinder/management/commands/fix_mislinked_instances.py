"""
Django management command to fix instances that are linked to wrong Name records.

This fixes cases where instances have a different type than their parent Name,
and reassigns them to a Name with matching type and name text.

Example: Šapinuwa person (ID 1667) has 84 place-type instances that should
belong to Šapinuwa place (ID 4960).
"""
from django.core.management.base import BaseCommand
from django.db import models, transaction
from django.db.models import Count, Q, F
from collections import defaultdict
from namefinder.models import Name, Instance, NameType


class Command(BaseCommand):
    help = 'Fix instances that are linked to Names with mismatched types'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually changing anything'
        )
        parser.add_argument(
            '--name',
            type=str,
            help='Only fix instances for a specific name (case-insensitive contains match)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        name_filter = options.get('name')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        
        # Find all instances where instance_type doesn't match name.name_type
        mismatched_instances = Instance.objects.exclude(
            instance_type=None
        ).exclude(
            name__name_type=None
        ).exclude(
            instance_type=F('name__name_type')
        ).select_related('name', 'name__name_type', 'instance_type', 'fragment')
        
        if name_filter:
            mismatched_instances = mismatched_instances.filter(
                name__name__icontains=name_filter
            )
        
        self.stdout.write(f'Found {mismatched_instances.count()} mismatched instances')
        
        if mismatched_instances.count() == 0:
            self.stdout.write(self.style.SUCCESS('No mismatched instances found!'))
            return
        
        # Group by (name_text, instance_type) to find where they should be reassigned
        reassignments = defaultdict(list)
        for instance in mismatched_instances:
            key = (instance.name.name, instance.instance_type.name if instance.instance_type else None)
            reassignments[key].append(instance)
        
        total_fixed = 0
        total_orphaned = 0
        
        with transaction.atomic():
            for (name_text, target_type), instances in reassignments.items():
                self.stdout.write(f'\n--- "{name_text}" instances with type "{target_type}" ---')
                self.stdout.write(f'  Currently linked to: {instances[0].name} (type: {instances[0].name.name_type})')
                self.stdout.write(f'  Count: {len(instances)} instances')
                
                # Find the correct Name record with matching name and type
                try:
                    target_type_obj = NameType.objects.get(name=target_type.lower()) if target_type else None
                    if target_type_obj:
                        correct_name = Name.objects.filter(
                            name=name_text,
                            name_type=target_type_obj
                        ).first()
                        
                        if correct_name:
                            self.stdout.write(self.style.SUCCESS(
                                f'  Found correct Name: ID={correct_name.pk}, type={correct_name.name_type}'
                            ))
                            
                            if not dry_run:
                                # Reassign all instances to the correct Name
                                for instance in instances:
                                    instance.name = correct_name
                                    instance.save(update_fields=['name'])
                                total_fixed += len(instances)
                                self.stdout.write(f'  Reassigned {len(instances)} instances')
                            else:
                                self.stdout.write(f'  Would reassign {len(instances)} instances')
                                total_fixed += len(instances)
                        else:
                            self.stdout.write(self.style.WARNING(
                                f'  No Name found with name="{name_text}" and type="{target_type}"'
                            ))
                            total_orphaned += len(instances)
                    else:
                        self.stdout.write(self.style.WARNING(
                            f'  No NameType found for "{target_type}"'
                        ))
                        total_orphaned += len(instances)
                        
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'  Error: {e}'))
                    total_orphaned += len(instances)
        
        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING(f'Would fix {total_fixed} instances'))
            self.stdout.write(self.style.WARNING(f'Would orphan {total_orphaned} instances (no matching Name found)'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Fixed {total_fixed} instances'))
            if total_orphaned > 0:
                self.stdout.write(self.style.WARNING(f'Could not fix {total_orphaned} instances (no matching Name found)'))
