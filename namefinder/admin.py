from django.contrib import admin
from .models import (
    NameType, WritingType, CompletenessType, PublicationType,
    Milieu, Series, Determinative, Fragment, Name, Instance
)


# =============================================================================
# Lookup Table Admins (Simple list display)
# =============================================================================

@admin.register(NameType)
class NameTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(WritingType)
class WritingTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(CompletenessType)
class CompletenessTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(PublicationType)
class PublicationTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(Milieu)
class MilieuAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(Determinative)
class DeterminativeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


# =============================================================================
# Main Table Admins
# =============================================================================

class InstanceInline(admin.TabularInline):
    """Inline display of instances in Name admin"""
    model = Instance
    extra = 0
    fields = ['fragment', 'line', 'spelling', 'instance_type', 'writing_type', 'determinative', 'completeness']
    autocomplete_fields = ['fragment']
    show_change_link = True


@admin.register(Fragment)
class FragmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'original_id', 'series_fragment', 'series', 'fragment_number', 'publication_type']
    list_filter = ['series', 'publication_type']
    search_fields = ['series_fragment', 'fragment_number', 'series__name']
    ordering = ['series__name', 'fragment_number']
    
    fieldsets = (
        (None, {
            'fields': ('original_id', 'series', 'fragment_number', 'series_fragment')
        }),
        ('Classification', {
            'fields': ('publication_type',)
        }),
    )


@admin.register(Name)
class NameAdmin(admin.ModelAdmin):
    list_display = ['id', 'original_id', 'name', 'name_type', 'writing_type', 'completeness', 'milieu', 'uncertain']
    list_filter = ['name_type', 'writing_type', 'completeness', 'milieu', 'uncertain']
    search_fields = ['name', 'query', 'variant_forms', 'correspondence']
    filter_horizontal = ['determinatives']
    ordering = ['query', 'name']
    inlines = [InstanceInline]
    
    fieldsets = (
        (None, {
            'fields': ('original_id', 'name', 'query')
        }),
        ('Classification', {
            'fields': ('name_type', 'writing_type', 'completeness', 'milieu', 'uncertain')
        }),
        ('Determinatives', {
            'fields': ('determinatives',)
        }),
        ('Related Information', {
            'fields': ('variant_forms', 'correspondence', 'literature'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'name_type', 'writing_type', 'completeness', 'milieu'
        ).prefetch_related('determinatives')


@admin.register(Instance)
class InstanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'original_id', 'name', 'fragment', 'line', 'spelling', 'instance_type', 'writing_type', 'completeness']
    list_filter = ['instance_type', 'writing_type', 'completeness', 'determinative']
    search_fields = ['name__name', 'fragment__series_fragment', 'spelling', 'line', 'notes']
    autocomplete_fields = ['name', 'fragment']
    ordering = ['name__name', 'fragment__series_fragment']
    
    fieldsets = (
        (None, {
            'fields': ('original_id', 'name', 'fragment', 'line')
        }),
        ('Details', {
            'fields': ('spelling', 'title_epithet')
        }),
        ('Classification', {
            'fields': ('instance_type', 'writing_type', 'determinative', 'completeness')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'name', 'fragment', 'instance_type', 'writing_type', 'determinative', 'completeness'
        )
