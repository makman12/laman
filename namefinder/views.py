import re
import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, OuterRef, Subquery, IntegerField, Value
from django.db.models.functions import Coalesce
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import (
    Name, Instance, Fragment, Series, PublicationType,
    NameType, WritingType, CompletenessType, Milieu, Determinative, DeterminativeVariant,
    DataReport, InstanceTLHMatch
)
from .forms import (
    LoginForm, NameForm, FragmentForm, InstanceForm, InstanceInlineForm,
    DeterminativeForm, DeterminativeVariantForm, DeterminativeMergeForm
)


def build_tlh_context(match_record):
    if match_record is None:
        return {
            'status': 'not_synced',
            'label': 'Not synced',
            'css_class': 'tlh-not-synced',
            'detail_lines': ['No persisted TLH match record yet. Run the sync command.'],
        }

    status = match_record.status
    detail_lines = []
    if match_record.doc_id:
        detail_lines.append(f"Doc: {match_record.doc_id}")

    matched_lines = match_record.matched_lines or []
    if matched_lines:
        line_preview = '; '.join(
            f"{line['line_number_raw']} => {(line['transliteration_plain'] or '').strip()}"
            for line in matched_lines[:2]
        )
        if len(matched_lines) > 2:
            line_preview += '; ...'
        detail_lines.append(f"Corpus lines: {line_preview}")

    if status == 'matched':
        detail_lines.append(
            f"Matched token: {match_record.suggested_spelling or '—'} [{match_record.suggested_determinative or '—'}]"
        )
    elif status == 'ambiguous_token':
        candidates = (match_record.candidates or [])[:4]
        if candidates:
            candidate_preview = '; '.join(
                f"{cand['raw_word']} [{cand['determinative'] or '—'}] <{cand.get('match_score', 0):.2f}>"
                for cand in candidates
            )
            detail_lines.append(f"Candidates: {candidate_preview}")
    elif status == 'line_not_found':
        targets = match_record.targets or []
        if targets:
            target_preview = ', '.join(target.get('label', '') for target in targets[:6] if target.get('label'))
            detail_lines.append(f"LAMAN targets: {target_preview}")
    elif status == 'no_name_token':
        detail_lines.append('Line matched, but no suitable token was found on the TLH line.')
    elif status == 'no_doc':
        detail_lines.append('Fragment reference did not resolve to a TLH document.')
    elif status == 'multiple_docs':
        detail_lines.append('Reference resolves to multiple TLH documents.')
    elif status == 'unparsed_line':
        detail_lines.append('LAMAN line notation could not be parsed.')

    labels = {
        'matched': 'Matched',
        'ambiguous_token': 'Ambiguous token',
        'line_not_found': 'Line not found',
        'no_name_token': 'No name token',
        'no_doc': 'No doc',
        'multiple_docs': 'Multiple docs',
        'unparsed_line': 'Unparsed line',
        'not_synced': 'Not synced',
    }
    return {
        'status': status,
        'label': labels.get(status, status.replace('_', ' ').title()),
        'css_class': f"tlh-{status.replace('_', '-')}",
        'detail_lines': detail_lines,
        'suggested_spelling': match_record.suggested_spelling,
        'suggested_determinative': match_record.suggested_determinative,
    }


def get_active_determinatives_queryset():
    return Determinative.objects.filter(is_active=True).order_by('name')


def merge_determinatives(source, target):
    if source.pk == target.pk:
        return

    target.ensure_preferred_variant()

    for name in source.names.all():
        name.determinatives.add(target)
        name.determinatives.remove(source)

    target_variants = {variant.value: variant for variant in target.variants.all()}
    for variant in list(source.variants.all()):
        existing = target_variants.get(variant.value)
        if existing:
            Instance.objects.filter(determinative_variant=variant).update(determinative_variant=existing)
            variant.delete()
            continue
        variant.determinative = target
        if variant.is_preferred and not target.preferred_variant:
            variant.is_preferred = True
        variant.save()
        target_variants[variant.value] = variant

    source.delete()


def index(request):
    """Main search page for names"""
    query = request.GET.get('q', '').strip()
    use_regex = request.GET.get('regex', '') == '1'
    selected_name_type = request.GET.get('name_type', '')
    selected_writing_type = request.GET.get('writing_type', '')
    selected_determinative = request.GET.get('determinative', '')
    selected_completeness = request.GET.get('completeness', '')
    selected_milieu = request.GET.get('milieu', '')
    selected_date = request.GET.get('date', '')
    show_fragmentary = request.GET.get('fragmentary', '') == '1'
    page_number = request.GET.get('page', 1)
    
    # Get filter options
    name_types = NameType.objects.all()
    instance_types = NameType.objects.all()
    writing_types = WritingType.objects.all()
    determinatives = get_active_determinatives_queryset()
    completeness_types = CompletenessType.objects.all()
    milieus = Milieu.objects.all()
    
    # Get distinct dates for filter dropdown
    date_choices = Fragment.objects.exclude(
        date__isnull=True
    ).exclude(date='').values_list('date', flat=True).distinct().order_by('date')
    
    names = Name.objects.select_related(
        'name_type', 'writing_type', 'completeness', 'milieu'
    )
    
    # Apply search
    if query:
        if use_regex:
            try:
                # Test if it's a valid regex
                re.compile(query)
                # Use regex on the query field (normalized)
                names = names.filter(
                    Q(query__iregex=query) | 
                    Q(name__iregex=query) |
                    Q(variant_forms__iregex=query)
                )
            except re.error:
                # Invalid regex, fall back to contains search
                names = names.filter(
                    Q(query__icontains=query) | 
                    Q(name__icontains=query)
                )
        else:
            # Normalize the search query for matching
            normalized_query = Name.normalize_for_search(query)
            names = names.filter(
                Q(query__icontains=normalized_query) | 
                Q(name__icontains=query) |
                Q(variant_forms__icontains=query)
            )
    
    # Apply filters
    if selected_name_type:
        names = names.filter(name_type_id=selected_name_type)
    if selected_writing_type:
        names = names.filter(writing_type_id=selected_writing_type)
    if selected_determinative:
        names = names.filter(instances__determinative_variant__determinative_id=selected_determinative).distinct()
    if selected_completeness:
        names = names.filter(completeness_id=selected_completeness)
    if selected_milieu:
        names = names.filter(milieu_id=selected_milieu)
    if selected_date:
        # Filter names that have at least one instance on a fragment with this date
        names = names.filter(instances__fragment__date=selected_date).distinct()
    if not show_fragmentary:
        names = names.filter(is_fragmentary=False)
    
    # Order results
    names = names.order_by('query', 'name')
    
    # Paginate
    paginator = Paginator(names, 50)  # 50 names per page
    page_obj = paginator.get_page(page_number)
    
    context = {
        'names': page_obj,
        'page_obj': page_obj,
        'query': query,
        'use_regex': use_regex,
        'name_types': name_types,
        'instance_types': instance_types,
        'writing_types': writing_types,
        'determinatives': determinatives,
        'completeness_types': completeness_types,
        'milieus': milieus,
        'date_choices': date_choices,
        'selected_name_type': selected_name_type,
        'selected_writing_type': selected_writing_type,
        'selected_determinative': selected_determinative,
        'selected_completeness': selected_completeness,
        'selected_milieu': selected_milieu,
        'selected_date': selected_date,
        'show_fragmentary': show_fragmentary,
    }
    
    return render(request, 'namefinder/index.html', context)


def name_detail(request, pk):
    """Detail page for a single name"""
    name = get_object_or_404(
        Name.objects.select_related(
            'name_type', 'writing_type', 'completeness', 'milieu'
        ).prefetch_related('determinatives'),
        pk=pk
    )
    
    instances = Instance.objects.filter(name=name).select_related(
        'fragment', 'fragment__series', 'instance_type',
        'writing_type', 'determinative_variant', 'determinative_variant__determinative', 'completeness'
    ).order_by('fragment__series__name', 'fragment__fragment_number', 'line')
    
    determinatives = name.determinatives.all()
    
    # Get co-occurring names (names that appear on the same fragments)
    fragment_ids = instances.values_list('fragment_id', flat=True).distinct()
    co_occurring = Name.objects.filter(
        instances__fragment_id__in=fragment_ids
    ).exclude(pk=pk).annotate(
        co_occurrence_count=Count('instances', filter=Q(instances__fragment_id__in=fragment_ids))
    ).select_related('name_type').order_by('-co_occurrence_count', 'name')[:50]  # Limit to top 50
    
    # Get all options for inline editing dropdowns
    name_types = NameType.objects.all()
    writing_types = WritingType.objects.all()
    completeness_types = CompletenessType.objects.all()
    milieus = Milieu.objects.all()
    all_determinatives = get_active_determinatives_queryset()
    # Note: fragments are loaded via AJAX autocomplete, not passed to context
    
    context = {
        'name': name,
        'instances': instances,
        'determinatives': determinatives,
        'co_occurring_names': co_occurring,
        # For inline editing
        'name_types': name_types,
        'writing_types': writing_types,
        'completeness_types': completeness_types,
        'milieus': milieus,
        'all_determinatives': all_determinatives,
        # For report modal
        'report_entry_type': 'name',
        'report_entry_id': name.pk,
        'report_entry_repr': name.name,
    }

    return render(request, 'namefinder/name_detail.html', context)


def fragment_search(request):
    """Search page for fragments with series/volume/fragment dropdowns"""
    selected_series = request.GET.get('series', '')
    selected_volume = request.GET.get('volume', '')
    selected_fragment = request.GET.get('fragment', '')

    series_list = Series.objects.annotate(
        fragment_count=Count('fragments')
    ).order_by('name')

    fragments_for_series = None
    volumes_for_series = []
    selected_series_name = ''

    if selected_series:
        try:
            series_obj = Series.objects.get(pk=selected_series)
            selected_series_name = series_obj.name
            fragments_for_series = Fragment.objects.filter(
                series_id=selected_series
            ).select_related('publication_type').prefetch_related('instances').order_by('fragment_number')

            # Extract distinct volumes from fragment numbers (part before the dot)
            all_numbers = fragments_for_series.values_list('fragment_number', flat=True)
            volume_set = set()
            for num in all_numbers:
                if '.' in num:
                    volume_set.add(num.split('.')[0])
            # Sort numerically where possible, alphabetically otherwise
            volumes_for_series = sorted(volume_set, key=lambda v: (int(v) if v.isdigit() else float('inf'), v))

            # Filter by volume if selected
            if selected_volume:
                fragments_for_series = fragments_for_series.filter(
                    fragment_number__startswith=selected_volume + '.'
                )
        except Series.DoesNotExist:
            pass

    context = {
        'series_list': series_list,
        'fragments_for_series': fragments_for_series,
        'volumes_for_series': volumes_for_series,
        'selected_series': selected_series,
        'selected_series_name': selected_series_name,
        'selected_volume': selected_volume,
        'selected_fragment': selected_fragment,
    }

    return render(request, 'namefinder/fragment_search.html', context)


def volume_detail(request, series_id, volume):
    """Detail page for a volume within a series, showing all fragments and attestations"""
    series = get_object_or_404(Series, pk=series_id)

    fragments = Fragment.objects.filter(
        series=series,
        fragment_number__startswith=volume + '.'
    ).select_related('publication_type').prefetch_related('instances').order_by('fragment_number')

    if not fragments.exists():
        from django.http import Http404
        raise Http404("No fragments found for this volume.")

    instances = Instance.objects.filter(
        fragment__in=fragments
    ).select_related(
        'name', 'name__name_type', 'instance_type', 'writing_type',
        'determinative_variant', 'determinative_variant__determinative', 'completeness', 'fragment'
    ).order_by('fragment__fragment_number', 'line', 'name__name')

    context = {
        'series': series,
        'volume': volume,
        'fragments': fragments,
        'instances': instances,
        'fragment_count': fragments.count(),
        'instance_count': instances.count(),
    }

    return render(request, 'namefinder/volume_detail.html', context)


def cth_search(request):
    """Search page for CTH (Catalogue des Textes Hittites) with dropdown"""
    import re
    import json
    
    selected_main_cth = request.GET.get('main_cth', '')
    selected_sub_cth = request.GET.get('sub_cth', '')
    
    # Get all distinct CTH numbers
    all_cth = Fragment.objects.exclude(
        cth__isnull=True
    ).exclude(cth='').values_list('cth', flat=True).distinct().order_by('cth')
    
    # Parse CTH numbers into main and sub parts
    # CTH format examples: "1", "1a", "1.I", "1.II.A", "376", "376.1", "376.A"
    cth_structure = {}  # main_cth -> list of full cth values
    
    for cth in all_cth:
        # Extract main CTH number (the leading numeric part)
        match = re.match(r'^(\d+)', str(cth))
        if match:
            main_num = match.group(1)
            if main_num not in cth_structure:
                cth_structure[main_num] = []
            cth_structure[main_num].append(cth)
    
    # Sort main CTH numbers numerically
    main_cth_list = sorted(cth_structure.keys(), key=lambda x: int(x))
    
    # Get sub-CTH options for selected main CTH
    sub_cth_list = []
    if selected_main_cth and selected_main_cth in cth_structure:
        sub_cth_list = cth_structure[selected_main_cth]
    
    context = {
        'main_cth_list': main_cth_list,
        'sub_cth_list': sub_cth_list,
        'cth_structure_json': json.dumps(cth_structure),
        'selected_main_cth': selected_main_cth,
        'selected_sub_cth': selected_sub_cth,
    }
    
    return render(request, 'namefinder/cth_search.html', context)


def cth_detail(request, cth_number):
    """Detail page for a CTH number showing all related fragments and attestations"""
    from urllib.parse import unquote
    import re
    cth_number = unquote(cth_number)
    
    # Check if this is a main CTH number (purely numeric) or specific sub-text
    is_main_cth = re.match(r'^\d+$', cth_number) is not None
    
    if is_main_cth:
        # For main CTH, get all fragments that start with this number
        fragments = Fragment.objects.filter(
            cth__regex=r'^' + cth_number + r'([^0-9]|$)'
        ).select_related(
            'series', 'publication_type'
        ).prefetch_related('instances', 'instances__name', 'instances__name__name_type').order_by('cth', 'series__name', 'fragment_number')
    else:
        # For specific sub-text, get exact match
        fragments = Fragment.objects.filter(cth=cth_number).select_related(
            'series', 'publication_type'
        ).prefetch_related('instances', 'instances__name', 'instances__name__name_type').order_by('series__name', 'fragment_number')
    
    # Get the CTH name from the first fragment (they should all have the same)
    cth_name = None
    cth_description = None
    if fragments.exists():
        first = fragments.first()
        cth_name = first.cth_name
        cth_description = first.cth_description
    
    # Get all attestations across these fragments
    if is_main_cth:
        all_instances = Instance.objects.filter(
            fragment__cth__regex=r'^' + cth_number + r'([^0-9]|$)'
        ).select_related(
            'name', 'name__name_type', 'fragment', 'fragment__series',
            'writing_type', 'determinative_variant', 'determinative_variant__determinative', 'completeness'
        ).order_by('fragment__cth', 'fragment__series__name', 'fragment__fragment_number', 'line')
    else:
        all_instances = Instance.objects.filter(
            fragment__cth=cth_number
        ).select_related(
            'name', 'name__name_type', 'fragment', 'fragment__series',
            'writing_type', 'determinative_variant', 'determinative_variant__determinative', 'completeness'
        ).order_by('fragment__series__name', 'fragment__fragment_number', 'line')
    
    # Count unique names
    unique_names = all_instances.values('name').distinct().count()
    
    # Get distinct sub-CTH numbers if this is a main CTH
    sub_cth_list = []
    if is_main_cth:
        sub_cth_list = list(fragments.values_list('cth', flat=True).distinct().order_by('cth'))
    
    context = {
        'cth_number': cth_number,
        'cth_name': cth_name,
        'cth_description': cth_description,
        'fragments': fragments,
        'instances': all_instances,
        'unique_names': unique_names,
        'is_main_cth': is_main_cth,
        'sub_cth_list': sub_cth_list,
    }
    
    return render(request, 'namefinder/cth_detail.html', context)


def fragment_detail(request, pk):
    """Detail page for a single fragment"""
    fragment = get_object_or_404(
        Fragment.objects.select_related('series', 'publication_type'),
        pk=pk
    )
    
    instances = Instance.objects.filter(fragment=fragment).select_related(
        'name', 'name__name_type', 'instance_type', 'writing_type', 'determinative_variant', 'determinative_variant__determinative', 'completeness'
    ).order_by('line', 'name__name')
    
    # Get all options for inline editing dropdowns
    series_list = Series.objects.all()
    publication_types = PublicationType.objects.all()
    name_types = NameType.objects.all()
    writing_types = WritingType.objects.all()
    all_determinatives = get_active_determinatives_queryset()
    all_names = Name.objects.select_related('name_type').order_by('name')
    
    context = {
        'fragment': fragment,
        'instances': instances,
        # For inline editing
        'series_list': series_list,
        'publication_types': publication_types,
        'name_types': name_types,
        'writing_types': writing_types,
        'all_determinatives': all_determinatives,
        'all_names': all_names,
        # For report modal
        'report_entry_type': 'fragment',
        'report_entry_id': fragment.pk,
        'report_entry_repr': fragment.series_fragment,
    }

    return render(request, 'namefinder/fragment_detail.html', context)


def about(request):
    """About page with statistics"""
    stats = {
        'names': Name.objects.count(),
        'instances': Instance.objects.count(),
        'fragments': Fragment.objects.count(),
        'series': Series.objects.count(),
    }
    
    context = {
        'stats': stats,
    }
    
    return render(request, 'namefinder/about.html', context)


def guide(request):
    """User guide page with documentation"""
    return render(request, 'namefinder/guide.html')


# =============================================================================
# Change Log Views
# =============================================================================

from .models import ChangeLog

@login_required
def changes(request):
    """View all changes made to the database"""
    # Get filter parameters
    action_filter = request.GET.get('action', '')
    model_filter = request.GET.get('model', '')
    user_filter = request.GET.get('user', '')
    page_number = request.GET.get('page', 1)
    
    changes = ChangeLog.objects.select_related('user', 'reverted_by').all()
    
    # Apply filters
    if action_filter:
        changes = changes.filter(action=action_filter)
    if model_filter:
        changes = changes.filter(model_type=model_filter)
    if user_filter:
        changes = changes.filter(user__username__icontains=user_filter)
    
    # Get unique users for filter dropdown
    from django.contrib.auth.models import User
    users_with_changes = User.objects.filter(change_logs__isnull=False).distinct()
    
    # Paginate
    paginator = Paginator(changes, 50)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'changes': page_obj,
        'page_obj': page_obj,
        'action_filter': action_filter,
        'model_filter': model_filter,
        'user_filter': user_filter,
        'users_with_changes': users_with_changes,
    }
    
    return render(request, 'namefinder/changes.html', context)


# =============================================================================
# CSV Export Views
# =============================================================================

def strip_html(text):
    """Remove HTML tags from text for CSV export"""
    if not text:
        return ''
    import re
    return re.sub(r'<[^>]+>', '', str(text))


def export_search_csv(request):
    """Export search results as CSV"""
    query = request.GET.get('q', '').strip()
    use_regex = request.GET.get('regex', '') == '1'
    selected_name_type = request.GET.get('name_type', '')
    selected_writing_type = request.GET.get('writing_type', '')
    selected_determinative = request.GET.get('determinative', '')
    selected_completeness = request.GET.get('completeness', '')
    selected_milieu = request.GET.get('milieu', '')
    selected_date = request.GET.get('date', '')
    show_fragmentary = request.GET.get('fragmentary', '') == '1'

    names = Name.objects.select_related(
        'name_type', 'writing_type', 'completeness', 'milieu'
    )

    # Apply search (same logic as index view)
    if query:
        if use_regex:
            try:
                re.compile(query)
                names = names.filter(
                    Q(query__iregex=query) | 
                    Q(name__iregex=query) |
                    Q(variant_forms__iregex=query)
                )
            except re.error:
                names = names.filter(
                    Q(query__icontains=query) | 
                    Q(name__icontains=query)
                )
        else:
            normalized_query = Name.normalize_for_search(query)
            names = names.filter(
                Q(query__icontains=normalized_query) | 
                Q(name__icontains=query) |
                Q(variant_forms__icontains=query)
            )
    
    # Apply filters
    if selected_name_type:
        names = names.filter(name_type_id=selected_name_type)
    if selected_writing_type:
        names = names.filter(writing_type_id=selected_writing_type)
    if selected_determinative:
        names = names.filter(instances__determinative_variant__determinative_id=selected_determinative).distinct()
    if selected_completeness:
        names = names.filter(completeness_id=selected_completeness)
    if selected_milieu:
        names = names.filter(milieu_id=selected_milieu)
    if selected_date:
        names = names.filter(instances__fragment__date=selected_date).distinct()
    if not show_fragmentary:
        names = names.filter(is_fragmentary=False)

    names = names.order_by('query', 'name')

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    filename = f'laman_search_results{"_" + query if query else ""}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow(['Name', 'Type', 'Writing Type', 'Completeness', 'Milieu', 'Variant Forms', 'Correspondence', 'Literature'])
    
    for name in names:
        writer.writerow([
            strip_html(name.name),
            name.name_type.name if name.name_type else '',
            name.writing_type.name if name.writing_type else '',
            name.completeness.name if name.completeness else '',
            name.milieu.name if name.milieu else '',
            strip_html(name.variant_forms) if name.variant_forms else '',
            strip_html(name.correspondence) if name.correspondence else '',
            name.literature or '',
        ])
    
    return response


def export_name_csv(request, pk):
    """Export attestations for a name as CSV"""
    name = get_object_or_404(Name, pk=pk)
    
    instances = Instance.objects.filter(name=name).select_related(
        'fragment', 'fragment__series', 'instance_type',
        'writing_type', 'determinative_variant', 'determinative_variant__determinative', 'completeness'
    ).order_by('fragment__series__name', 'fragment__fragment_number', 'line')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    safe_name = strip_html(name.name).replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="laman_{safe_name}_attestations.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Name', 'Fragment', 'Line', 'Spelling', 'Writing Type', 'Determinative Spelling', 'Determinative', 'Title/Epithet', 'Completeness'])
    
    for inst in instances:
        writer.writerow([
            strip_html(name.name),
            inst.fragment.series_fragment if inst.fragment else '',
            inst.line or '',
            strip_html(inst.spelling) if inst.spelling else '',
            inst.writing_type.name if inst.writing_type else '',
            inst.display_determinative or '',
            inst.determinative.name if inst.determinative else '',
            inst.title_epithet or '',
            inst.completeness.name if inst.completeness else '',
        ])
    
    return response


def export_fragment_csv(request, pk):
    """Export attestations for a fragment as CSV"""
    fragment = get_object_or_404(Fragment.objects.select_related('series'), pk=pk)
    
    instances = Instance.objects.filter(fragment=fragment).select_related(
        'name', 'name__name_type', 'instance_type', 
        'writing_type', 'determinative_variant', 'determinative_variant__determinative', 'completeness'
    ).order_by('line', 'name__name')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    safe_fragment = fragment.series_fragment.replace(' ', '_').replace('/', '-')
    response['Content-Disposition'] = f'attachment; filename="laman_{safe_fragment}_names.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Fragment', 'Name', 'Name Type', 'Line', 'Spelling', 'Writing Type', 'Determinative Spelling', 'Determinative', 'Title/Epithet', 'Completeness'])
    
    for inst in instances:
        writer.writerow([
            fragment.series_fragment,
            strip_html(inst.name.name) if inst.name else '',
            inst.name.name_type.name if inst.name and inst.name.name_type else '',
            inst.line or '',
            strip_html(inst.spelling) if inst.spelling else '',
            inst.writing_type.name if inst.writing_type else '',
            inst.display_determinative or '',
            inst.determinative.name if inst.determinative else '',
            inst.title_epithet or '',
            inst.completeness.name if inst.completeness else '',
        ])
    
    return response


# =============================================================================
# Authentication Views
# =============================================================================

def user_login(request):
    """Login view"""
    if request.user.is_authenticated:
        return redirect('namefinder:index')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.GET.get('next', 'namefinder:index')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    
    return render(request, 'namefinder/login.html', {'form': form})


def user_logout(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('namefinder:index')


# =============================================================================
# Name CRUD Views
# =============================================================================

@login_required
def name_create(request):
    """Create a new name"""
    if request.method == 'POST':
        form = NameForm(request.POST)
        if form.is_valid():
            name = form.save()
            messages.success(request, f'Name "{name.name}" created successfully.')
            return redirect('namefinder:name_detail', pk=name.pk)
    else:
        form = NameForm()
    
    return render(request, 'namefinder/name_form.html', {
        'form': form,
        'action': 'Create',
        'title': 'Create New Name',
    })


@login_required
def name_edit(request, pk):
    """Edit an existing name"""
    name = get_object_or_404(Name, pk=pk)
    
    if request.method == 'POST':
        form = NameForm(request.POST, instance=name)
        if form.is_valid():
            form.save()
            messages.success(request, f'Name "{name.name}" updated successfully.')
            return redirect('namefinder:name_detail', pk=name.pk)
    else:
        form = NameForm(instance=name)
    
    return render(request, 'namefinder/name_form.html', {
        'form': form,
        'action': 'Edit',
        'title': f'Edit: {name.name}',
        'object': name,
    })


@login_required
def determinative_manager(request):
    """Dedicated manager for determinatives and orphan variants."""
    create_form = DeterminativeForm(prefix='create')
    merge_form = DeterminativeMergeForm(prefix='merge')
    show_zero = request.GET.get('show_zero') == '1'

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            create_form = DeterminativeForm(request.POST, prefix='create')
            if create_form.is_valid():
                determinative = create_form.save()
                determinative.ensure_preferred_variant()
                messages.success(request, f'Determinative "{determinative.name}" created successfully.')
                return redirect('namefinder:determinative_detail', pk=determinative.pk)
        elif action == 'merge':
            merge_form = DeterminativeMergeForm(request.POST, prefix='merge')
            if merge_form.is_valid():
                merge_determinatives(
                    merge_form.cleaned_data['source'],
                    merge_form.cleaned_data['target'],
                )
                messages.success(request, 'Determinatives merged successfully.')
                return redirect('namefinder:determinative_manager')
        elif action == 'map_orphan':
            variant = get_object_or_404(DeterminativeVariant, pk=request.POST.get('variant_id'))
            target = get_object_or_404(Determinative, pk=request.POST.get('target_determinative'))
            variant.determinative = target
            variant.is_preferred = False
            variant.save()
            messages.success(request, f'Variant "{variant.value}" mapped to {target.name}.')
            return redirect('namefinder:determinative_manager')

    name_count_subq = Name.determinatives.through.objects.filter(
        determinative_id=OuterRef('pk')
    ).values('determinative_id').annotate(
        c=Count('*')
    ).values('c')[:1]
    variant_count_subq = DeterminativeVariant.objects.filter(
        determinative_id=OuterRef('pk')
    ).values('determinative_id').annotate(
        c=Count('*')
    ).values('c')[:1]
    instance_count_subq = Instance.objects.filter(
        determinative_variant__determinative_id=OuterRef('pk')
    ).values('determinative_variant__determinative_id').annotate(
        c=Count('*')
    ).values('c')[:1]

    determinatives = Determinative.objects.annotate(
        name_count=Coalesce(Subquery(name_count_subq, output_field=IntegerField()), Value(0)),
        instance_count=Coalesce(Subquery(instance_count_subq, output_field=IntegerField()), Value(0)),
        variant_count=Coalesce(Subquery(variant_count_subq, output_field=IntegerField()), Value(0)),
    ).order_by('name')
    orphan_variants = DeterminativeVariant.objects.filter(determinative__isnull=True).annotate(
        instance_count=Count('instances', distinct=True)
    )
    if not show_zero:
        orphan_variants = orphan_variants.filter(instance_count__gt=0)
    orphan_variants = orphan_variants.order_by('-instance_count', 'value')

    return render(request, 'namefinder/determinative_manager.html', {
        'create_form': create_form,
        'merge_form': merge_form,
        'determinatives': determinatives,
        'orphan_variants': orphan_variants,
        'show_zero': show_zero,
        'active_section': 'determinatives',
    })


@login_required
def determinative_detail(request, pk):
    """Manage one determinative and its mapped variants."""
    determinative = get_object_or_404(
        Determinative.objects.prefetch_related('variants', 'names'),
        pk=pk,
    )

    edit_form = DeterminativeForm(instance=determinative, prefix='det')
    variant_form = DeterminativeVariantForm(prefix='variant')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_determinative':
            edit_form = DeterminativeForm(request.POST, instance=determinative, prefix='det')
            if edit_form.is_valid():
                edit_form.save()
                messages.success(request, 'Determinative updated successfully.')
                return redirect('namefinder:determinative_detail', pk=determinative.pk)
        elif action == 'delete_determinative':
            if determinative.names.exists():
                messages.error(request, 'Cannot delete a determinative that is linked to names.')
                return redirect('namefinder:determinative_detail', pk=determinative.pk)
            if determinative.variants.filter(instances__isnull=False).exists():
                messages.error(request, 'Cannot delete a determinative that is linked to attestations.')
                return redirect('namefinder:determinative_detail', pk=determinative.pk)
            det_name = determinative.name
            determinative.delete()
            messages.success(request, f'Determinative "{det_name}" deleted successfully.')
            return redirect('namefinder:determinative_manager')
        elif action == 'add_variant':
            variant_form = DeterminativeVariantForm(request.POST, prefix='variant')
            if variant_form.is_valid():
                variant = variant_form.save(commit=False)
                variant.determinative = determinative
                variant.save()
                if variant.is_preferred or not determinative.variants.filter(is_preferred=True).exists():
                    determinative.ensure_preferred_variant()
                messages.success(request, f'Variant "{variant.value}" added.')
                return redirect('namefinder:determinative_detail', pk=determinative.pk)
        elif action == 'update_variant':
            variant = get_object_or_404(DeterminativeVariant, pk=request.POST.get('variant_id'), determinative=determinative)
            variant_form = DeterminativeVariantForm(request.POST, instance=variant, prefix='variant')
            if variant_form.is_valid():
                variant = variant_form.save(commit=False)
                variant.determinative = determinative
                variant.save()
                messages.success(request, 'Variant updated successfully.')
                return redirect('namefinder:determinative_detail', pk=determinative.pk)
        elif action == 'delete_variant':
            variant = get_object_or_404(DeterminativeVariant, pk=request.POST.get('variant_id'), determinative=determinative)
            if variant.instances.exists():
                messages.error(request, 'Cannot delete a variant that is still linked to attestations.')
            else:
                variant.delete()
                if determinative.variants.exists() and not determinative.variants.filter(is_preferred=True).exists():
                    determinative.ensure_preferred_variant()
                messages.success(request, 'Variant deleted successfully.')
            return redirect('namefinder:determinative_detail', pk=determinative.pk)

    variants = determinative.variants.annotate(instance_count=Count('instances', distinct=True)).order_by('-is_preferred', 'value')
    return render(request, 'namefinder/determinative_detail.html', {
        'determinative': determinative,
        'edit_form': edit_form,
        'variant_form': variant_form,
        'variants': variants,
    })


@login_required
def name_delete(request, pk):
    """Delete a name"""
    name = get_object_or_404(Name, pk=pk)
    
    if request.method == 'POST':
        name_str = str(name.name)
        name.delete()
        messages.success(request, f'Name "{name_str}" deleted successfully.')
        return redirect('namefinder:index')
    
    return render(request, 'namefinder/confirm_delete.html', {
        'object': name,
        'object_type': 'Name',
        'cancel_url': 'namefinder:name_detail',
    })


# =============================================================================
# Fragment CRUD Views
# =============================================================================

@login_required
def fragment_create(request):
    """Create a new fragment"""
    if request.method == 'POST':
        form = FragmentForm(request.POST)
        if form.is_valid():
            fragment = form.save()
            messages.success(request, f'Fragment "{fragment.series_fragment}" created successfully.')
            return redirect('namefinder:fragment_detail', pk=fragment.pk)
    else:
        form = FragmentForm()
    
    return render(request, 'namefinder/fragment_form.html', {
        'form': form,
        'action': 'Create',
        'title': 'Create New Fragment',
    })


@login_required
def fragment_edit(request, pk):
    """Edit an existing fragment"""
    fragment = get_object_or_404(Fragment, pk=pk)
    
    if request.method == 'POST':
        form = FragmentForm(request.POST, instance=fragment)
        if form.is_valid():
            form.save()
            messages.success(request, f'Fragment "{fragment.series_fragment}" updated successfully.')
            return redirect('namefinder:fragment_detail', pk=fragment.pk)
    else:
        form = FragmentForm(instance=fragment)
    
    return render(request, 'namefinder/fragment_form.html', {
        'form': form,
        'action': 'Edit',
        'title': f'Edit: {fragment.series_fragment}',
        'object': fragment,
    })


@login_required
def fragment_delete(request, pk):
    """Delete a fragment"""
    fragment = get_object_or_404(Fragment, pk=pk)
    
    if request.method == 'POST':
        fragment_str = str(fragment.series_fragment)
        fragment.delete()
        messages.success(request, f'Fragment "{fragment_str}" deleted successfully.')
        return redirect('namefinder:fragment_search')
    
    return render(request, 'namefinder/confirm_delete.html', {
        'object': fragment,
        'object_type': 'Fragment',
        'cancel_url': 'namefinder:fragment_detail',
    })


# =============================================================================
# Instance (Attestation) CRUD Views
# =============================================================================

@login_required
def instance_create(request):
    """Create a new instance"""
    # Pre-populate from query params
    name_id = request.GET.get('name')
    fragment_id = request.GET.get('fragment')
    
    initial = {}
    if name_id:
        initial['name'] = name_id
    if fragment_id:
        initial['fragment'] = fragment_id
    
    if request.method == 'POST':
        form = InstanceForm(request.POST)
        if form.is_valid():
            instance = form.save()
            messages.success(request, 'Attestation created successfully.')
            # Redirect back to the appropriate page
            if name_id:
                return redirect('namefinder:name_detail', pk=name_id)
            elif fragment_id:
                return redirect('namefinder:fragment_detail', pk=fragment_id)
            return redirect('namefinder:index')
    else:
        form = InstanceForm(initial=initial)
    
    return render(request, 'namefinder/instance_form.html', {
        'form': form,
        'action': 'Create',
        'title': 'Create New Attestation',
    })


@login_required
def instance_edit(request, pk):
    """Edit an existing instance"""
    instance = get_object_or_404(Instance, pk=pk)
    modal_mode = request.GET.get('modal') == '1'
    next_url = request.GET.get('next') or request.POST.get('next') or ''
    
    if request.method == 'POST':
        form = InstanceForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attestation updated successfully.')
            if modal_mode:
                redirect_url = request.path
                query_params = ['modal=1', 'saved=1']
                if next_url:
                    query_params.append(f'next={next_url}')
                return redirect(f'{redirect_url}?{"&".join(query_params)}')
            if instance.name:
                return redirect('namefinder:name_detail', pk=instance.name.pk)
            return redirect('namefinder:index')
    else:
        form = InstanceForm(instance=instance)
    
    return render(request, 'namefinder/instance_form.html', {
        'form': form,
        'action': 'Edit',
        'title': 'Edit Attestation',
        'object': instance,
        'modal_mode': modal_mode,
        'saved': request.GET.get('saved') == '1',
        'next_url': next_url,
    })


@login_required
def instance_delete(request, pk):
    """Delete an instance"""
    instance = get_object_or_404(Instance, pk=pk)
    name_pk = instance.name.pk if instance.name else None
    
    if request.method == 'POST':
        instance.delete()
        messages.success(request, 'Attestation deleted successfully.')
        if name_pk:
            return redirect('namefinder:name_detail', pk=name_pk)
        return redirect('namefinder:index')
    
    return render(request, 'namefinder/confirm_delete.html', {
        'object': instance,
        'object_type': 'Attestation',
        'cancel_url': 'namefinder:name_detail' if name_pk else 'namefinder:index',
        'cancel_pk': name_pk,
    })


# =============================================================================
# Data Problems (Admin Only)
# =============================================================================

@login_required
def data_problems(request):
    """Admin page listing data quality issues that need manual review"""
    active_tab = request.GET.get('tab', 'fragmentary')

    # Counts for tabs
    report_count = DataReport.objects.filter(status='open').count()
    fragmentary_count = Name.objects.filter(is_fragmentary=True).count()

    context = {
        'active_tab': active_tab,
        'report_count': report_count,
        'fragmentary_count': fragmentary_count,
    }

    if active_tab == 'reports':
        show_resolved = request.GET.get('resolved', '') == '1'
        if show_resolved:
            reports = DataReport.objects.all().order_by('-created_at')
        else:
            reports = DataReport.objects.filter(status='open').order_by('-created_at')
        context['reports'] = reports
        context['show_resolved'] = show_resolved

    elif active_tab == 'fragmentary':
        fragmentary_names = Name.objects.filter(is_fragmentary=True).select_related(
            'name_type'
        ).annotate(
            instance_count=Count('instances')
        ).order_by('name')

        # Build list of non-fragmentary names for matching
        non_frag = Name.objects.filter(is_fragmentary=False).select_related('name_type')
        non_frag_list = [(n.pk, n.name, n.name_type.name if n.name_type else '') for n in non_frag]

        def strip_frag(name):
            """Strip fragmentary markers to get searchable root."""
            s = name
            for ch in ['[', ']', '…', '?', '(?)']:
                s = s.replace(ch, '')
            s = s.strip(' -–')
            return s

        def find_matches(frag_name):
            """Find non-fragmentary names that could match a fragmentary name."""
            root = strip_frag(frag_name).lower()
            if len(root) < 2:
                return []
            matches = []
            for pk, nname, ntype in non_frag_list:
                if root in nname.lower():
                    matches.append({'pk': pk, 'name': nname, 'type': ntype})
            # Sort by name length (shorter = more likely exact match)
            matches.sort(key=lambda m: len(m['name']))
            return matches[:10]  # Cap at 10

        frag_with = [n for n in fragmentary_names if n.instance_count > 0]
        frag_without = [n for n in fragmentary_names if n.instance_count == 0]

        frag_with_data = []
        for n in frag_with:
            matches = find_matches(n.name)
            frag_with_data.append({
                'name': n,
                'instance_count': n.instance_count,
                'matches': matches,
                'match_count': len(matches),
            })

        frag_without_data = []
        for n in frag_without:
            matches = find_matches(n.name)
            frag_without_data.append({
                'name': n,
                'matches': matches,
                'match_count': len(matches),
            })

        context['frag_with_attestations'] = frag_with_data
        context['frag_without_attestations'] = frag_without_data

    return render(request, 'namefinder/data_problems.html', context)


# =============================================================================
# Attestation Search
# =============================================================================

def attestation_search(request):
    """Search page for attestations (instances) independent of names"""
    query = request.GET.get('q', '').strip()
    selected_name_type = request.GET.get('name_type', '')
    selected_writing_type = request.GET.get('writing_type', '')
    selected_determinative = request.GET.get('determinative', '')
    selected_completeness = request.GET.get('completeness', '')
    selected_series = request.GET.get('series', '')
    selected_tlh_status = request.GET.get('tlh_status', '')
    show_unlinked = request.GET.get('unlinked', '') == '1'
    show_tlh_unsynced = request.GET.get('tlh_unsynced', '') == '1'
    page_number = request.GET.get('page', 1)

    # Get filter options
    name_types = NameType.objects.all()
    writing_types = WritingType.objects.all()
    determinatives = get_active_determinatives_queryset()
    completeness_types = CompletenessType.objects.all()
    series_list = Series.objects.annotate(
        instance_count=Count('fragments__instances')
    ).filter(instance_count__gt=0).order_by('name')
    tlh_status_choices = [('not_synced', 'Not synced')] + list(InstanceTLHMatch.STATUS_CHOICES)

    instances = Instance.objects.select_related(
        'name', 'name__name_type', 'fragment', 'fragment__series',
        'instance_type', 'writing_type', 'determinative_variant',
        'determinative_variant__determinative', 'completeness',
        'tlh_match_record'
    )

    # Text search across spelling, name, fragment
    if query:
        instances = instances.filter(
            Q(spelling__icontains=query) |
            Q(name__name__icontains=query) |
            Q(fragment__series_fragment__icontains=query) |
            Q(line__icontains=query) |
            Q(notes__icontains=query) |
            Q(title_epithet__icontains=query)
        )

    # Apply filters
    if selected_name_type:
        instances = instances.filter(name__name_type_id=selected_name_type)
    if selected_writing_type:
        instances = instances.filter(writing_type_id=selected_writing_type)
    if selected_determinative:
        instances = instances.filter(determinative_variant__determinative_id=selected_determinative)
    if selected_completeness:
        instances = instances.filter(completeness_id=selected_completeness)
    if selected_series:
        instances = instances.filter(fragment__series_id=selected_series)
    if show_unlinked:
        instances = instances.filter(name__isnull=True)
    if selected_tlh_status == 'not_synced':
        instances = instances.filter(tlh_match_record__isnull=True)
    elif selected_tlh_status:
        instances = instances.filter(tlh_match_record__status=selected_tlh_status)
    if show_tlh_unsynced:
        instances = instances.filter(tlh_match_record__isnull=True)

    instances = instances.order_by('fragment__series__name', 'fragment__fragment_number', 'line')

    # Paginate
    paginator = Paginator(instances, 50)
    page_obj = paginator.get_page(page_number)
    for instance in page_obj.object_list:
        instance.tlh_match = build_tlh_context(getattr(instance, 'tlh_match_record', None))

    context = {
        'instances': page_obj,
        'page_obj': page_obj,
        'query': query,
        'name_types': name_types,
        'writing_types': writing_types,
        'determinatives': determinatives,
        'completeness_types': completeness_types,
        'series_list': series_list,
        'tlh_status_choices': tlh_status_choices,
        'selected_name_type': selected_name_type,
        'selected_writing_type': selected_writing_type,
        'selected_determinative': selected_determinative,
        'selected_completeness': selected_completeness,
        'selected_series': selected_series,
        'selected_tlh_status': selected_tlh_status,
        'show_unlinked': show_unlinked,
        'show_tlh_unsynced': show_tlh_unsynced,
    }

    return render(request, 'namefinder/attestation_search.html', context)


# =============================================================================
# Network Visualization
# =============================================================================

def network(request):
    """Network visualization page for co-occurrence of names"""
    return render(request, 'namefinder/network.html')
