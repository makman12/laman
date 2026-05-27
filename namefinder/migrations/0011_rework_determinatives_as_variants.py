from django.db import migrations, models
import django.db.models.deletion
import re


def clean_variant_value(text):
    if text is None:
        return ""
    cleaned = str(text).replace('°', '').strip()
    return re.sub(r'\s+', ' ', cleaned)


def normalize_name(text):
    normalized = clean_variant_value(text)
    if not normalized:
        return ""
    for ch in ['[', ']', '⸢', '⸣', '〈', '〉', '?', '!', '(', ')']:
        normalized = normalized.replace(ch, '')
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    normalized = normalized.strip('- ').strip()
    if normalized in {'', '—', '---'}:
        return ""
    return normalized


def letter_runs(text):
    return re.findall(r"[^\W\d_]+", text, flags=re.UNICODE)


def is_valid_parent_name(text):
    normalized = normalize_name(text)
    if not normalized:
        return False
    if normalized.startswith('_'):
        return False
    if not any(ch.isalpha() for ch in normalized):
        return False
    for run in letter_runs(normalized):
        if any(ch.islower() for ch in run):
            if run not in {'d', 'm', 'f'}:
                return False
    return True


def classify_kind(value, has_parent):
    cleaned = clean_variant_value(value)
    if cleaned in {'', '—', '---'} or cleaned.lower().startswith('br'):
        return 'placeholder'
    if any(ch in cleaned for ch in ['[', ']', '⸢', '⸣', '〈', '〉', '?', '!']):
        return 'restored'
    if not has_parent:
        return 'editorial'
    return 'standard'


def forwards(apps, schema_editor):
    Determinative = apps.get_model('namefinder', 'Determinative')
    DeterminativeVariant = apps.get_model('namefinder', 'DeterminativeVariant')
    Name = apps.get_model('namefinder', 'Name')
    Instance = apps.get_model('namefinder', 'Instance')
    NameDeterminative = Name.determinatives.through

    old_dets = list(Determinative.objects.all().order_by('id'))
    parent_by_name = {}
    old_to_parent = {}

    for det in old_dets:
        if not is_valid_parent_name(det.name):
            old_to_parent[det.id] = None
            continue
        normalized = normalize_name(det.name)
        parent = parent_by_name.get(normalized)
        if parent is None:
            parent = Determinative.objects.filter(name=normalized).first()
            if parent is None:
                parent = Determinative.objects.create(name=normalized, is_active=True)
            else:
                parent.is_active = True
                parent.save(update_fields=['is_active'])
            parent_by_name[normalized] = parent
        old_to_parent[det.id] = parent.id

    variant_cache = {}

    def get_or_create_variant(parent_id, value, is_preferred=False):
        cleaned = clean_variant_value(value)
        if not cleaned:
            return None
        key = (parent_id, cleaned)
        if key in variant_cache:
            variant = variant_cache[key]
            if is_preferred and not variant.is_preferred:
                variant.is_preferred = True
                variant.save(update_fields=['is_preferred'])
            return variant

        variant, created = DeterminativeVariant.objects.get_or_create(
            determinative_id=parent_id,
            value=cleaned,
            defaults={
                'variant_kind': classify_kind(cleaned, parent_id is not None),
                'is_preferred': is_preferred,
            },
        )
        changed = []
        desired_kind = classify_kind(cleaned, parent_id is not None)
        if variant.variant_kind != desired_kind:
            variant.variant_kind = desired_kind
            changed.append('variant_kind')
        if is_preferred and not variant.is_preferred:
            variant.is_preferred = True
            changed.append('is_preferred')
        if changed:
            variant.save(update_fields=changed)
        variant_cache[key] = variant
        return variant

    for parent in parent_by_name.values():
        get_or_create_variant(parent.id, parent.name, is_preferred=True)

    for det in old_dets:
        parent_id = old_to_parent.get(det.id)
        get_or_create_variant(parent_id, det.name, is_preferred=(parent_id is not None and clean_variant_value(det.name) == Determinative.objects.get(id=parent_id).name))

    existing_links = list(NameDeterminative.objects.all().values_list('name_id', 'determinative_id'))
    NameDeterminative.objects.all().delete()

    rebuilt_links = []
    seen_links = set()
    for name_id, old_det_id in existing_links:
        parent_id = old_to_parent.get(old_det_id)
        if not parent_id:
            continue
        key = (name_id, parent_id)
        if key in seen_links:
            continue
        seen_links.add(key)
        rebuilt_links.append(NameDeterminative(name_id=name_id, determinative_id=parent_id))
    if rebuilt_links:
        NameDeterminative.objects.bulk_create(rebuilt_links)

    old_det_names = {det.id: det.name for det in old_dets}
    for instance in Instance.objects.all().iterator():
        old_det_id = instance.determinative_id
        display_value = clean_variant_value(instance.raw_determinative)
        if not display_value and old_det_id:
            display_value = clean_variant_value(old_det_names.get(old_det_id, ''))

        parent_id = old_to_parent.get(old_det_id)
        if parent_id is None and display_value and is_valid_parent_name(display_value):
            normalized = normalize_name(display_value)
            parent = parent_by_name.get(normalized)
            if parent is None:
                parent = Determinative.objects.create(name=normalized, is_active=True)
                parent_by_name[normalized] = parent
                get_or_create_variant(parent.id, parent.name, is_preferred=True)
            parent_id = parent.id

        variant = None
        if display_value:
            variant = get_or_create_variant(parent_id, display_value, is_preferred=(parent_id is not None and display_value == Determinative.objects.get(id=parent_id).name))
        elif parent_id:
            variant = get_or_create_variant(parent_id, Determinative.objects.get(id=parent_id).name, is_preferred=True)

        instance.determinative_variant_id = variant.id if variant else None
        instance.save(update_fields=['determinative_variant'])


def cleanup_old_determinatives(apps, schema_editor):
    Determinative = apps.get_model('namefinder', 'Determinative')
    Determinative.objects.filter(names__isnull=True, variants__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('namefinder', '0010_canonicalize_determinatives'),
    ]

    operations = [
        migrations.AddField(
            model_name='determinative',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Whether this determinative should appear in normal user pickers'),
        ),
        migrations.CreateModel(
            name='DeterminativeVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=100)),
                ('variant_kind', models.CharField(choices=[('standard', 'Standard'), ('restored', 'Restored/Damaged'), ('editorial', 'Editorial/Unmapped'), ('placeholder', 'Placeholder')], default='standard', max_length=20)),
                ('is_preferred', models.BooleanField(default=False, help_text='Preferred display variant for the parent determinative')),
                ('determinative', models.ForeignKey(blank=True, help_text='Normalized parent determinative; blank for unmapped/noisy values', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='variants', to='namefinder.determinative')),
            ],
            options={
                'verbose_name': 'Determinative Variant',
                'verbose_name_plural': 'Determinative Variants',
                'ordering': ['determinative__name', 'value'],
                'constraints': [models.UniqueConstraint(fields=('determinative', 'value'), name='unique_determinative_variant_value')],
            },
        ),
        migrations.AddField(
            model_name='instance',
            name='determinative_variant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='instances', to='namefinder.determinativevariant'),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='instance',
            name='raw_determinative',
        ),
        migrations.RemoveField(
            model_name='instance',
            name='determinative',
        ),
        migrations.RunPython(cleanup_old_determinatives, migrations.RunPython.noop),
    ]
