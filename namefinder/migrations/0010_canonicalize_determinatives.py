from django.db import migrations, models
import re


def clean_raw_value(text):
    if text is None:
        return ""
    cleaned = str(text).replace('°', '').strip()
    return re.sub(r'\s+', ' ', cleaned)


def normalize_determinative_name(text):
    normalized = clean_raw_value(text)
    if not normalized:
        return ""

    for ch in ['[', ']', '⸢', '⸣', '〈', '〉', '?', '!', '(', ')']:
        normalized = normalized.replace(ch, '')

    normalized = re.sub(r'\s+', ' ', normalized).strip()
    normalized = normalized.strip('-')
    if normalized in {'', '—', '---'}:
        return ""
    return normalized


def forwards(apps, schema_editor):
    Determinative = apps.get_model('namefinder', 'Determinative')
    Name = apps.get_model('namefinder', 'Name')
    Instance = apps.get_model('namefinder', 'Instance')
    NameDeterminative = Name.determinatives.through

    old_to_canonical = {}
    canonical_ids = {}

    for det in Determinative.objects.all().order_by('id'):
        canonical_name = normalize_determinative_name(det.name)
        if not canonical_name:
            old_to_canonical[det.id] = None
            continue

        canonical = Determinative.objects.filter(name=canonical_name).first()
        if canonical is None:
            canonical = Determinative.objects.create(name=canonical_name)
        canonical_ids[canonical_name] = canonical.id
        old_to_canonical[det.id] = canonical.id

    for instance in Instance.objects.all().iterator():
        raw_value = ""
        if instance.determinative_id:
            det = Determinative.objects.filter(id=instance.determinative_id).first()
            raw_value = clean_raw_value(det.name) if det else ""

        instance.raw_determinative = raw_value
        instance.determinative_id = old_to_canonical.get(instance.determinative_id)
        instance.save(update_fields=['raw_determinative', 'determinative'])

    existing_links = list(NameDeterminative.objects.all().values_list('name_id', 'determinative_id'))
    NameDeterminative.objects.all().delete()

    rebuilt_links = []
    seen = set()
    for name_id, old_det_id in existing_links:
        canonical_id = old_to_canonical.get(old_det_id)
        if canonical_id is None:
            continue
        key = (name_id, canonical_id)
        if key in seen:
            continue
        seen.add(key)
        rebuilt_links.append(NameDeterminative(name_id=name_id, determinative_id=canonical_id))

    if rebuilt_links:
        NameDeterminative.objects.bulk_create(rebuilt_links)

    Determinative.objects.exclude(
        id__in=NameDeterminative.objects.values_list('determinative_id', flat=True)
    ).exclude(
        id__in=Instance.objects.exclude(determinative_id__isnull=True).values_list('determinative_id', flat=True)
    ).delete()


def backwards(apps, schema_editor):
    Instance = apps.get_model('namefinder', 'Instance')
    for instance in Instance.objects.all().iterator():
        instance.raw_determinative = ""
        instance.save(update_fields=['raw_determinative'])


class Migration(migrations.Migration):

    dependencies = [
        ('namefinder', '0009_instancetlhmatch'),
    ]

    operations = [
        migrations.AddField(
            model_name='instance',
            name='raw_determinative',
            field=models.CharField(blank=True, default='', help_text='Exact attested/editorial determinative form as entered in the source data', max_length=100),
        ),
        migrations.RunPython(forwards, backwards),
    ]
