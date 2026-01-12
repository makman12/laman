import re
import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import (
    Name, Instance, Fragment, Series, PublicationType,
    NameType, WritingType, CompletenessType, Milieu, Determinative
)
from .forms import (
    LoginForm, NameForm, FragmentForm, InstanceForm, InstanceInlineForm
)


def index(request):
    """Main search page for names"""
    query = request.GET.get('q', '').strip()
    use_regex = request.GET.get('regex', '') == '1'
    selected_name_type = request.GET.get('name_type', '')
    selected_writing_type = request.GET.get('writing_type', '')
    selected_completeness = request.GET.get('completeness', '')
    selected_milieu = request.GET.get('milieu', '')
    page_number = request.GET.get('page', 1)
    
    # Get filter options
    name_types = NameType.objects.all()
    writing_types = WritingType.objects.all()
    completeness_types = CompletenessType.objects.all()
    milieus = Milieu.objects.all()
    
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
    if selected_completeness:
        names = names.filter(completeness_id=selected_completeness)
    if selected_milieu:
        names = names.filter(milieu_id=selected_milieu)
    
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
        'writing_types': writing_types,
        'completeness_types': completeness_types,
        'milieus': milieus,
        'selected_name_type': selected_name_type,
        'selected_writing_type': selected_writing_type,
        'selected_completeness': selected_completeness,
        'selected_milieu': selected_milieu,
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
        'writing_type', 'determinative', 'completeness'
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
    all_determinatives = Determinative.objects.all()
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
    }
    
    return render(request, 'namefinder/name_detail.html', context)


def fragment_search(request):
    """Search page for fragments with series/fragment dropdowns"""
    selected_series = request.GET.get('series', '')
    selected_fragment = request.GET.get('fragment', '')
    
    series_list = Series.objects.annotate(
        fragment_count=Count('fragments')
    ).order_by('name')
    
    fragments_for_series = None
    selected_series_name = ''
    
    if selected_series:
        try:
            series_obj = Series.objects.get(pk=selected_series)
            selected_series_name = series_obj.name
            fragments_for_series = Fragment.objects.filter(
                series_id=selected_series
            ).select_related('publication_type').prefetch_related('instances').order_by('fragment_number')
        except Series.DoesNotExist:
            pass
    
    context = {
        'series_list': series_list,
        'fragments_for_series': fragments_for_series,
        'selected_series': selected_series,
        'selected_series_name': selected_series_name,
        'selected_fragment': selected_fragment,
    }
    
    return render(request, 'namefinder/fragment_search.html', context)


def fragment_detail(request, pk):
    """Detail page for a single fragment"""
    fragment = get_object_or_404(
        Fragment.objects.select_related('series', 'publication_type'),
        pk=pk
    )
    
    instances = Instance.objects.filter(fragment=fragment).select_related(
        'name', 'instance_type', 'writing_type', 'determinative', 'completeness'
    ).order_by('line', 'name__name')
    
    # Get all options for inline editing dropdowns
    series_list = Series.objects.all()
    publication_types = PublicationType.objects.all()
    name_types = NameType.objects.all()
    writing_types = WritingType.objects.all()
    all_determinatives = Determinative.objects.all()
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
    selected_completeness = request.GET.get('completeness', '')
    selected_milieu = request.GET.get('milieu', '')
    
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
    if selected_completeness:
        names = names.filter(completeness_id=selected_completeness)
    if selected_milieu:
        names = names.filter(milieu_id=selected_milieu)
    
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
        'writing_type', 'determinative', 'completeness'
    ).order_by('fragment__series__name', 'fragment__fragment_number', 'line')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    safe_name = strip_html(name.name).replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="laman_{safe_name}_attestations.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Name', 'Fragment', 'Line', 'Spelling', 'Writing Type', 'Determinative', 'Title/Epithet', 'Completeness'])
    
    for inst in instances:
        writer.writerow([
            strip_html(name.name),
            inst.fragment.series_fragment if inst.fragment else '',
            inst.line or '',
            strip_html(inst.spelling) if inst.spelling else '',
            inst.writing_type.name if inst.writing_type else '',
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
        'writing_type', 'determinative', 'completeness'
    ).order_by('line', 'name__name')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    safe_fragment = fragment.series_fragment.replace(' ', '_').replace('/', '-')
    response['Content-Disposition'] = f'attachment; filename="laman_{safe_fragment}_names.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Fragment', 'Name', 'Name Type', 'Line', 'Spelling', 'Writing Type', 'Determinative', 'Title/Epithet', 'Completeness'])
    
    for inst in instances:
        writer.writerow([
            fragment.series_fragment,
            strip_html(inst.name.name) if inst.name else '',
            inst.name.name_type.name if inst.name and inst.name.name_type else '',
            inst.line or '',
            strip_html(inst.spelling) if inst.spelling else '',
            inst.writing_type.name if inst.writing_type else '',
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
    
    if request.method == 'POST':
        form = InstanceForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attestation updated successfully.')
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
# Network Visualization
# =============================================================================

def network(request):
    """Network visualization page for co-occurrence of names"""
    name_types = NameType.objects.all()
    milieus = Milieu.objects.all()
    
    # Get all series for filter
    series_list = Series.objects.annotate(
        fragment_count=Count('fragments')
    ).filter(fragment_count__gt=0).order_by('name')
    
    context = {
        'name_types': name_types,
        'series_list': series_list,
    }
    return render(request, 'namefinder/network.html', context)
