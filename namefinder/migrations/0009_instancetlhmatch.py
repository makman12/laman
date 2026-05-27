from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('namefinder', '0008_add_datareport_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='InstanceTLHMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('matched', 'Matched'), ('ambiguous_token', 'Ambiguous token'), ('line_not_found', 'Line not found'), ('no_name_token', 'No name token'), ('no_doc', 'No doc'), ('multiple_docs', 'Multiple docs'), ('unparsed_line', 'Unparsed line')], db_index=True, max_length=32)),
                ('doc_id', models.CharField(blank=True, max_length=255)),
                ('suggested_spelling', models.TextField(blank=True)),
                ('suggested_determinative', models.CharField(blank=True, max_length=100)),
                ('targets', models.JSONField(blank=True, default=list)),
                ('matched_lines', models.JSONField(blank=True, default=list)),
                ('candidates', models.JSONField(blank=True, default=list)),
                ('extra_data', models.JSONField(blank=True, default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('instance', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='tlh_match_record', to='namefinder.instance')),
            ],
            options={
                'verbose_name': 'Instance TLH Match',
                'verbose_name_plural': 'Instance TLH Matches',
                'ordering': ['instance_id'],
            },
        ),
    ]
