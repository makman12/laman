from django.db import models
from django.contrib.auth.models import User
import re
import unicodedata
import json


# =============================================================================
# Lookup Tables (Reference Tables)
# =============================================================================

class NameType(models.Model):
    """Lookup table for name types: place, person, deity"""
    name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        verbose_name = "Name Type"
        verbose_name_plural = "Name Types"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class WritingType(models.Model):
    """Lookup table for writing types: phonetic, logographic, hieroglyphic, akkadographic"""
    name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        verbose_name = "Writing Type"
        verbose_name_plural = "Writing Types"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class CompletenessType(models.Model):
    """Lookup table for completeness: complete, incomplete, acephalous"""
    name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        verbose_name = "Completeness Type"
        verbose_name_plural = "Completeness Types"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class PublicationType(models.Model):
    """Lookup table for publication status: Publication, Other, Inventory"""
    name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        verbose_name = "Publication Type"
        verbose_name_plural = "Publication Types"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Milieu(models.Model):
    """Lookup table for cultural context: unc, WS, Hattian, Mes, Syr, Hur"""
    name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        verbose_name = "Milieu"
        verbose_name_plural = "Milieus"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Series(models.Model):
    """Lookup table for publication series: KBo, KUB, BoHa, etc."""
    name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        verbose_name = "Series"
        verbose_name_plural = "Series"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Determinative(models.Model):
    """Lookup table for determinatives (classifier symbols)"""
    name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        verbose_name = "Determinative"
        verbose_name_plural = "Determinatives"
        ordering = ['name']
    
    def __str__(self):
        return self.name


# =============================================================================
# Main Tables
# =============================================================================

class Fragment(models.Model):
    """
    Text fragments/tablets from which names are attested.
    Each fragment belongs to a series and has a fragment number.
    """
    original_id = models.IntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="Original Fragment_ID from the Excel file (null for new records)"
    )
    series = models.ForeignKey(
        Series,
        on_delete=models.PROTECT,
        related_name='fragments'
    )
    fragment_number = models.CharField(
        max_length=100,
        help_text="Fragment number within series (e.g., '51.108')"
    )
    series_fragment = models.CharField(
        max_length=200,
        help_text="Combined series + fragment (e.g., 'KBo 51.108')",
        db_index=True
    )
    publication_type = models.ForeignKey(
        PublicationType,
        on_delete=models.PROTECT,
        related_name='fragments',
        null=True,
        blank=True
    )
    
    # CTH (Catalogue des Textes Hittites) information
    cth = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="CTH number (e.g., '530.53', '700')"
    )
    cth_name = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="CTH text name"
    )
    cth_description = models.TextField(
        null=True,
        blank=True,
        help_text="CTH description"
    )
    
    # Archaeological/Museum information
    inventory_number = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Museum inventory number"
    )
    find_spot = models.TextField(
        null=True,
        blank=True,
        help_text="Archaeological find spot information"
    )
    
    # Dating information
    date = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Date or period (e.g., 'jh', 'sjh', 'mh')"
    )
    date_uncertain = models.BooleanField(
        default=False,
        help_text="Whether the date is uncertain"
    )
    
    # Additional metadata
    comments = models.TextField(
        null=True,
        blank=True,
        help_text="Additional comments or notes"
    )
    is_matched = models.BooleanField(
        default=False,
        help_text="Whether this fragment was matched to CTH data"
    )
    match_method = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Method used to match this fragment"
    )
    
    class Meta:
        verbose_name = "Fragment"
        verbose_name_plural = "Fragments"
        ordering = ['series__name', 'fragment_number']
    
    def __str__(self):
        return self.series_fragment
    
    def save(self, *args, **kwargs):
        # Auto-generate series_fragment if not provided
        if not self.series_fragment and self.series:
            self.series_fragment = f"{self.series.name} {self.fragment_number}"
        super().save(*args, **kwargs)


class Name(models.Model):
    """
    Unique name entries in the database.
    Each name has associated metadata and can have multiple instances (attestations).
    """
    original_id = models.IntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="Original Name_ID from the Excel file (null for new records)"
    )
    name = models.CharField(
        max_length=500,
        db_index=True,
        help_text="The attested name"
    )
    name_type = models.ForeignKey(
        NameType,
        on_delete=models.PROTECT,
        related_name='names',
        null=True,
        blank=True
    )
    writing_type = models.ForeignKey(
        WritingType,
        on_delete=models.PROTECT,
        related_name='names',
        null=True,
        blank=True
    )
    completeness = models.ForeignKey(
        CompletenessType,
        on_delete=models.PROTECT,
        related_name='names',
        null=True,
        blank=True
    )
    milieu = models.ForeignKey(
        Milieu,
        on_delete=models.PROTECT,
        related_name='names',
        null=True,
        blank=True
    )
    determinatives = models.ManyToManyField(
        Determinative,
        related_name='names',
        blank=True,
        help_text="Determinatives used with this name"
    )
    variant_forms = models.TextField(
        blank=True,
        null=True,
        help_text="Variant spellings of the name"
    )
    correspondence = models.TextField(
        blank=True,
        null=True,
        help_text="Corresponding names in other traditions"
    )
    literature = models.TextField(
        blank=True,
        null=True,
        help_text="Bibliography references"
    )
    query = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        db_index=True,
        help_text="Normalized version for searching"
    )
    uncertain = models.BooleanField(
        default=False,
        help_text="Whether this name is uncertain"
    )
    
    class Meta:
        verbose_name = "Name"
        verbose_name_plural = "Names"
        ordering = ['query', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Auto-generate query field for searching (combines name, variants, correspondence)
        parts = []
        if self.name:
            parts.append(self.name)
        if self.variant_forms:
            parts.append(self.variant_forms)
        if self.correspondence:
            parts.append(self.correspondence)
        
        if parts:
            combined = ' '.join(parts)
            self.query = self.normalize_for_search(combined)
        super().save(*args, **kwargs)
    
    @staticmethod
    def normalize_for_search(text):
        """
        Normalize text for searching:
        1. Strip HTML tags
        2. Lowercase
        3. Remove accents (ḫ→h, š→s, etc.)
        4. Normalize similar sounds (g=k, b=p, d=t)
        5. Remove punctuation
        6. Collapse repeated letters
        """
        if not text:
            return ""
        
        # Remove HTML tags (like <sup>, <i>, <sub>, etc.)
        text = re.sub(r'<[^>]+>', '', text)
        
        # Lowercase
        text = text.lower()
        
        # Unicode normalization - decompose accented characters
        text = unicodedata.normalize('NFD', text)
        
        # Remove combining diacritical marks
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        
        # Special character replacements
        replacements = {
            'ḫ': 'h', 'ḥ': 'h',
            'š': 's', 'ṣ': 's',
            'ṭ': 't', 'ț': 't',
            'ž': 'z',
            'ʾ': '', 'ʿ': '',
            ''': '', ''': '',
            '-': '', '_': '',
            '.': '', ',': '',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Normalize similar sounds
        sound_map = {
            'g': 'k',
            'b': 'p',
            'd': 't',
        }
        for old, new in sound_map.items():
            text = text.replace(old, new)
        
        # Remove non-alphanumeric characters
        text = re.sub(r'[^a-z0-9]', '', text)
        
        # Collapse repeated letters
        text = re.sub(r'(.)\1+', r'\1', text)
        
        return text


class Instance(models.Model):
    """
    Individual attestations of names in fragments.
    Each instance represents a name appearing in a specific location of a text.
    """
    original_id = models.IntegerField(
        unique=True,
        null=True,
        blank=True,
        help_text="Original Instance_ID from the Excel file (null for new records)"
    )
    name = models.ForeignKey(
        Name,
        on_delete=models.CASCADE,
        related_name='instances',
        null=True,
        blank=True
    )
    fragment = models.ForeignKey(
        Fragment,
        on_delete=models.CASCADE,
        related_name='instances',
        null=True,
        blank=True
    )
    title_epithet = models.TextField(
        blank=True,
        null=True,
        help_text="Title or epithet of the name"
    )
    spelling = models.TextField(
        blank=True,
        null=True,
        help_text="How the name is spelled in this instance"
    )
    instance_type = models.ForeignKey(
        NameType,
        on_delete=models.PROTECT,
        related_name='instances',
        null=True,
        blank=True,
        help_text="Type: place, deity, person"
    )
    writing_type = models.ForeignKey(
        WritingType,
        on_delete=models.PROTECT,
        related_name='instances',
        null=True,
        blank=True
    )
    determinative = models.ForeignKey(
        Determinative,
        on_delete=models.PROTECT,
        related_name='instances',
        null=True,
        blank=True
    )
    line = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Line reference in the fragment"
    )
    completeness = models.ForeignKey(
        CompletenessType,
        on_delete=models.PROTECT,
        related_name='instances',
        null=True,
        blank=True
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes"
    )
    
    class Meta:
        verbose_name = "Instance"
        verbose_name_plural = "Instances"
        ordering = ['name__name', 'fragment__series_fragment']
    
    def __str__(self):
        name_str = self.name.name if self.name else "Unknown"
        fragment_str = self.fragment.series_fragment if self.fragment else "Unknown Fragment"
        return f"{name_str} in {fragment_str}"


# =============================================================================
# Change Log / Audit Trail
# =============================================================================

class ChangeLog(models.Model):
    """Tracks all changes made to the database for audit and revert purposes"""
    
    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
    ]
    
    MODEL_CHOICES = [
        ('name', 'Name'),
        ('fragment', 'Fragment'),
        ('instance', 'Attestation'),
        ('series', 'Series'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='change_logs'
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_type = models.CharField(max_length=20, choices=MODEL_CHOICES)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    object_repr = models.CharField(max_length=255, help_text="String representation of the object")
    
    # Store old and new data as JSON for revert capability
    old_data = models.JSONField(null=True, blank=True, help_text="Data before the change")
    new_data = models.JSONField(null=True, blank=True, help_text="Data after the change")
    
    # Change summary for display
    change_summary = models.TextField(blank=True, help_text="Human-readable summary of changes")
    
    timestamp = models.DateTimeField(auto_now_add=True)
    reverted = models.BooleanField(default=False)
    reverted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reverted_changes'
    )
    reverted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Change Log"
        verbose_name_plural = "Change Logs"
        ordering = ['-timestamp']
    
    def __str__(self):
        user_str = self.user.username if self.user else "Unknown"
        return f"{user_str} {self.get_action_display()} {self.model_type}: {self.object_repr}"
    
    @classmethod
    def log_change(cls, user, action, model_type, obj, old_data=None, new_data=None):
        """Helper method to create a change log entry"""
        change_summary = cls._generate_summary(action, old_data, new_data)
        
        return cls.objects.create(
            user=user,
            action=action,
            model_type=model_type,
            object_id=obj.pk if obj and hasattr(obj, 'pk') else None,
            object_repr=str(obj)[:255] if obj else "Deleted",
            old_data=old_data,
            new_data=new_data,
            change_summary=change_summary
        )
    
    @staticmethod
    def _generate_summary(action, old_data, new_data):
        """Generate a human-readable summary of changes"""
        if action == 'create':
            return "New record created"
        elif action == 'delete':
            return "Record deleted"
        elif action == 'update' and old_data and new_data:
            changes = []
            for key in new_data:
                old_val = old_data.get(key)
                new_val = new_data.get(key)
                if old_val != new_val:
                    old_display = old_val if old_val else '(empty)'
                    new_display = new_val if new_val else '(empty)'
                    changes.append(f"{key}: '{old_display}' → '{new_display}'")
            return "; ".join(changes) if changes else "No changes detected"
        return ""
