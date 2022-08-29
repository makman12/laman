from django.db import models


class Name(models.Model):
    name_id = models.IntegerField(db_column='Name ID', primary_key=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    writing_clean = models.TextField(db_column='Writing_clean', blank=True, null=True)  # Field name made lowercase.
    det_2 = models.TextField(db_column='Det_2', blank=True, null=True)  # Field name made lowercase.
    det_1 = models.TextField(db_column='Det_1', blank=True, null=True)  # Field name made lowercase.
    other_classifier_data = models.TextField(db_column='Other classifier data', blank=True, null=True)  # Field name made lowercase. Field renamed to remove unsuitable characters.
    name_clean = models.TextField(db_column='Name_clean', blank=True, null=True)  # Field name made lowercase.
    correspondence = models.TextField(db_column='Correspondence', blank=True, null=True)  # Field name made lowercase.
    milieu = models.TextField(db_column='Milieu', blank=True, null=True)  # Field name made lowercase.
    linguistic_analysis = models.TextField(db_column='Linguistic_analysis', blank=True, null=True)  # Field name made lowercase.
    literature = models.TextField(db_column='Literature', blank=True, null=True)  # Field name made lowercase.
    dn_clean = models.TextField(db_column='DN_clean', blank=True, null=True)  # Field name made lowercase.
    type = models.TextField(db_column='Type', blank=True, null=True)  # Field name made lowercase.
    completeness = models.TextField(db_column='Completeness', blank=True, null=True)  # Field name made lowercase.
    variant_forms = models.TextField(db_column='Variant_Forms', blank=True, null=True)  # Field name made lowercase.
    query = models.TextField(db_column='Query', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'name'
        ordering = ('query',)

    def __str__(self):
        return self.name_clean

class Instance(models.Model):
    name_id = models.ForeignKey('Name', models.DO_NOTHING, db_column='Name ID', blank=True, null=True) 
    dn = models.TextField(db_column='DN', blank=True, null=True)  # Field name made lowercase.
    epithet = models.TextField(db_column='Epithet', blank=True, null=True)  # Field name made lowercase.
    occurrence = models.TextField(db_column='Occurrence', blank=True, null=True)  # Field name made lowercase.
    writing = models.TextField(db_column='Writing', blank=True, null=True)  # Field name made lowercase.
    determinative = models.TextField(db_column='Determinative', blank=True, null=True)  # Field name made lowercase.
    dn_transc = models.TextField(blank=True, null=True)
    series = models.TextField(blank=True, null=True)
    volume = models.TextField(blank=True, null=True)
    fragment = models.TextField(blank=True, null=True)
    line = models.TextField(blank=True, null=True)
    notes = models.TextField(db_column='Notes', blank=True, null=True)  # Field name made lowercase.
    type = models.TextField(blank=True, null=True)
    incomplete = models.TextField(blank=True, null=True)
    acephalous = models.TextField(blank=True, null=True)
    logogram_begin = models.TextField(blank=True, null=True)
    hieroglyphic = models.TextField(blank=True, null=True)
    hieroglyphic_begin = models.TextField(blank=True, null=True)
    name = models.TextField(db_column='Name', blank=True, null=True)  # Field name made lowercase.
    spelling = models.TextField(db_column='Spelling', blank=True, null=True)  # Field name made lowercase.
    title = models.TextField(db_column='Title', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'instance'
        ordering =('occurrence',)

    def __str__(self):
        return self.name
