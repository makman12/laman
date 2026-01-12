"""
API views for AJAX inline editing
"""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q
from .models import Name, Instance, Fragment, Series, NameType, WritingType, CompletenessType, Milieu, Determinative, ChangeLog


def get_name_data(name):
    """Extract name data as dict for logging"""
    return {
        'name': name.name,
        'name_type': name.name_type.name if name.name_type else None,
        'writing_type': name.writing_type.name if name.writing_type else None,
        'completeness': name.completeness.name if name.completeness else None,
        'milieu': name.milieu.name if name.milieu else None,
        'uncertain': name.uncertain,
        'variant_forms': name.variant_forms,
        'correspondence': name.correspondence,
        'literature': name.literature,
    }


def get_instance_data(instance):
    """Extract instance data as dict for logging"""
    return {
        'name': instance.name.name if instance.name else None,
        'fragment': instance.fragment.series_fragment if instance.fragment else None,
        'line': instance.line,
        'spelling': instance.spelling,
        'writing_type': instance.writing_type.name if instance.writing_type else None,
        'determinative': instance.determinative.name if instance.determinative else None,
        'title_epithet': instance.title_epithet,
    }


def get_fragment_data(fragment):
    """Extract fragment data as dict for logging"""
    return {
        'series': fragment.series.name if fragment.series else None,
        'fragment_number': fragment.fragment_number,
        'publication_type': fragment.publication_type.name if fragment.publication_type else None,
    }


@login_required
@require_http_methods(["PUT"])
@csrf_protect
def api_name_update(request, pk):
    """Update a name via AJAX"""
    try:
        name = Name.objects.get(pk=pk)
        old_data = get_name_data(name)
        data = json.loads(request.body)
        
        name.name = data.get('name', name.name)
        
        # Handle foreign keys
        name_type_id = data.get('name_type')
        name.name_type_id = name_type_id if name_type_id else None
        
        writing_type_id = data.get('writing_type')
        name.writing_type_id = writing_type_id if writing_type_id else None
        
        completeness_id = data.get('completeness')
        name.completeness_id = completeness_id if completeness_id else None
        
        milieu_id = data.get('milieu')
        name.milieu_id = milieu_id if milieu_id else None
        
        name.uncertain = data.get('uncertain', False)
        name.variant_forms = data.get('variant_forms', '')
        name.correspondence = data.get('correspondence', '')
        name.literature = data.get('literature', '')
        
        name.save()
        
        # Log the change
        new_data = get_name_data(name)
        ChangeLog.log_change(request.user, 'update', 'name', name, old_data, new_data)
        
        return JsonResponse({'success': True, 'id': name.id})
    except Name.DoesNotExist:
        return JsonResponse({'error': 'Name not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["DELETE"])
@csrf_protect
def api_name_delete(request, pk):
    """Delete a name via AJAX"""
    try:
        name = Name.objects.get(pk=pk)
        old_data = get_name_data(name)
        object_repr = str(name)
        
        # Log before delete
        ChangeLog.objects.create(
            user=request.user,
            action='delete',
            model_type='name',
            object_id=pk,
            object_repr=object_repr,
            old_data=old_data,
            change_summary=f"Deleted name: {name.name}"
        )
        
        name.delete()
        return JsonResponse({'success': True})
    except Name.DoesNotExist:
        return JsonResponse({'error': 'Name not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
@csrf_protect
def api_instance_create(request):
    """Create a new instance via AJAX"""
    try:
        data = json.loads(request.body)
        
        instance = Instance(
            name_id=data.get('name'),
            fragment_id=data.get('fragment'),
            line=data.get('line', ''),
            spelling=data.get('spelling', ''),
            title_epithet=data.get('title_epithet', ''),
        )
        
        # Handle optional foreign keys
        writing_type_id = data.get('writing_type')
        if writing_type_id:
            instance.writing_type_id = writing_type_id
            
        determinative_id = data.get('determinative')
        if determinative_id:
            instance.determinative_id = determinative_id
            
        instance_type_id = data.get('instance_type')
        if instance_type_id:
            instance.instance_type_id = instance_type_id
            
        completeness_id = data.get('completeness')
        if completeness_id:
            instance.completeness_id = completeness_id
        
        instance.save()
        
        # Log the creation
        new_data = get_instance_data(instance)
        ChangeLog.log_change(request.user, 'create', 'instance', instance, None, new_data)
        
        return JsonResponse({'success': True, 'id': instance.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["PUT"])
@csrf_protect
def api_instance_update(request, pk):
    """Update an instance via AJAX"""
    try:
        instance = Instance.objects.get(pk=pk)
        old_data = get_instance_data(instance)
        data = json.loads(request.body)
        
        fragment_id = data.get('fragment')
        if fragment_id:
            instance.fragment_id = fragment_id
            
        instance.line = data.get('line', '')
        instance.spelling = data.get('spelling', '')
        instance.title_epithet = data.get('title_epithet', '')
        
        writing_type_id = data.get('writing_type')
        instance.writing_type_id = writing_type_id if writing_type_id else None
        
        determinative_id = data.get('determinative')
        instance.determinative_id = determinative_id if determinative_id else None
        
        instance.save()
        
        # Log the change
        new_data = get_instance_data(instance)
        ChangeLog.log_change(request.user, 'update', 'instance', instance, old_data, new_data)
        
        return JsonResponse({'success': True, 'id': instance.id})
    except Instance.DoesNotExist:
        return JsonResponse({'error': 'Instance not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["DELETE"])
@csrf_protect
def api_instance_delete(request, pk):
    """Delete an instance via AJAX"""
    try:
        instance = Instance.objects.get(pk=pk)
        old_data = get_instance_data(instance)
        object_repr = str(instance)
        
        # Log before delete
        ChangeLog.objects.create(
            user=request.user,
            action='delete',
            model_type='instance',
            object_id=pk,
            object_repr=object_repr,
            old_data=old_data,
            change_summary=f"Deleted attestation: {object_repr}"
        )
        
        instance.delete()
        return JsonResponse({'success': True})
    except Instance.DoesNotExist:
        return JsonResponse({'error': 'Instance not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["PUT"])
@csrf_protect
def api_fragment_update(request, pk):
    """Update a fragment via AJAX"""
    try:
        fragment = Fragment.objects.get(pk=pk)
        old_data = get_fragment_data(fragment)
        data = json.loads(request.body)
        
        series_id = data.get('series')
        if series_id:
            fragment.series_id = series_id
            
        fragment.fragment_number = data.get('fragment_number', fragment.fragment_number)
        
        publication_type_id = data.get('publication_type')
        fragment.publication_type_id = publication_type_id if publication_type_id else None
        
        fragment.save()
        
        # Log the change
        new_data = get_fragment_data(fragment)
        ChangeLog.log_change(request.user, 'update', 'fragment', fragment, old_data, new_data)
        
        return JsonResponse({'success': True, 'id': fragment.id})
    except Fragment.DoesNotExist:
        return JsonResponse({'error': 'Fragment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["DELETE"])
@csrf_protect
def api_fragment_delete(request, pk):
    """Delete a fragment via AJAX"""
    try:
        fragment = Fragment.objects.get(pk=pk)
        old_data = get_fragment_data(fragment)
        object_repr = str(fragment)
        
        # Log before delete
        ChangeLog.objects.create(
            user=request.user,
            action='delete',
            model_type='fragment',
            object_id=pk,
            object_repr=object_repr,
            old_data=old_data,
            change_summary=f"Deleted fragment: {object_repr}"
        )
        
        fragment.delete()
        return JsonResponse({'success': True})
    except Fragment.DoesNotExist:
        return JsonResponse({'error': 'Fragment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_fragment_search(request):
    """Search fragments by series and number for autocomplete"""
    query = request.GET.get('q', '').strip()
    if len(query) < 1:
        return JsonResponse({'fragments': []})
    
    # Check if query contains a space (e.g., "KUB 1" or "KUB 1.")
    parts = query.split(None, 1)  # Split on first whitespace
    
    if len(parts) == 2:
        # Query has both series and number part (e.g., "KUB 1")
        series_part, number_part = parts
        fragments = Fragment.objects.select_related('series').filter(
            series__name__icontains=series_part,
            fragment_number__istartswith=number_part
        )
    else:
        # Single term - search in series name OR fragment number
        fragments = Fragment.objects.select_related('series').filter(
            series__name__icontains=query
        ) | Fragment.objects.select_related('series').filter(
            fragment_number__icontains=query
        )
    
    fragments = fragments.order_by('series__name', 'fragment_number')[:50]
    
    result = [{
        'id': f.id,
        'text': f'{f.series.name} {f.fragment_number}',
        'series': f.series.name,
        'number': f.fragment_number
    } for f in fragments]
    
    return JsonResponse({'fragments': result})


@login_required
@require_http_methods(["POST"])
@csrf_protect
def api_fragment_create(request):
    """Create a new fragment via AJAX, with series warning check"""
    try:
        data = json.loads(request.body)
        series_name = data.get('series_name', '').strip()
        fragment_number = data.get('fragment_number', '').strip()
        
        if not series_name or not fragment_number:
            return JsonResponse({'error': 'Series name and fragment number are required'}, status=400)
        
        # Check if this exact fragment already exists
        existing = Fragment.objects.filter(
            series__name__iexact=series_name,
            fragment_number__iexact=fragment_number
        ).first()
        
        if existing:
            return JsonResponse({
                'success': True, 
                'id': existing.id, 
                'text': f'{existing.series.name} {existing.fragment_number}',
                'existing': True
            })
        
        # Check if series exists
        series = Series.objects.filter(name__iexact=series_name).first()
        new_series = False
        
        if not series:
            # Series doesn't exist - this needs confirmation
            new_series = True
            # Check if user confirmed creating new series
            if not data.get('confirm_new_series'):
                # Get similar series names to suggest
                similar = Series.objects.filter(name__icontains=series_name[:3])[:5]
                similar_names = [s.name for s in similar]
                return JsonResponse({
                    'needs_confirmation': True,
                    'message': f'Series "{series_name}" does not exist. This might be a typo.',
                    'similar_series': similar_names
                })
            
            # Create new series and log it
            series = Series.objects.create(name=series_name)
            ChangeLog.objects.create(
                user=request.user,
                action='create',
                model_type='series',
                object_id=series.pk,
                object_repr=str(series),
                new_data={'name': series_name},
                change_summary=f"Created new series: {series_name}"
            )
        
        # Create the fragment
        fragment = Fragment.objects.create(
            series=series,
            fragment_number=fragment_number
        )
        
        # Log the fragment creation
        new_data = get_fragment_data(fragment)
        ChangeLog.log_change(request.user, 'create', 'fragment', fragment, None, new_data)
        
        return JsonResponse({
            'success': True,
            'id': fragment.id,
            'text': f'{series.name} {fragment_number}',
            'new_series': new_series,
            'existing': False
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
@csrf_protect
def api_revert_change(request, pk):
    """Revert a change from the change log"""
    from django.utils import timezone
    
    try:
        change = ChangeLog.objects.get(pk=pk)
        
        if change.reverted:
            return JsonResponse({'error': 'This change has already been reverted'}, status=400)
        
        model_map = {
            'name': Name,
            'fragment': Fragment,
            'instance': Instance,
            'series': Series,
        }
        
        model_class = model_map.get(change.model_type)
        if not model_class:
            return JsonResponse({'error': 'Unknown model type'}, status=400)
        
        if change.action == 'create':
            # Revert create = delete the object
            try:
                obj = model_class.objects.get(pk=change.object_id)
                obj.delete()
            except model_class.DoesNotExist:
                pass  # Already deleted
                
        elif change.action == 'delete':
            # Revert delete = recreate the object
            if change.old_data:
                # Map the stored data back to model fields
                recreate_data = {}
                old_data = change.old_data
                
                if change.model_type == 'name':
                    recreate_data['name'] = old_data.get('name', '')
                    if old_data.get('name_type'):
                        nt = NameType.objects.filter(name=old_data['name_type']).first()
                        if nt: recreate_data['name_type'] = nt
                    if old_data.get('writing_type'):
                        wt = WritingType.objects.filter(name=old_data['writing_type']).first()
                        if wt: recreate_data['writing_type'] = wt
                    if old_data.get('completeness'):
                        ct = CompletenessType.objects.filter(name=old_data['completeness']).first()
                        if ct: recreate_data['completeness'] = ct
                    if old_data.get('milieu'):
                        m = Milieu.objects.filter(name=old_data['milieu']).first()
                        if m: recreate_data['milieu'] = m
                    recreate_data['uncertain'] = old_data.get('uncertain', False)
                    recreate_data['variant_forms'] = old_data.get('variant_forms', '')
                    recreate_data['correspondence'] = old_data.get('correspondence', '')
                    recreate_data['literature'] = old_data.get('literature', '')
                    model_class.objects.create(**recreate_data)
                    
                elif change.model_type == 'fragment':
                    if old_data.get('series'):
                        series = Series.objects.filter(name=old_data['series']).first()
                        if series:
                            recreate_data['series'] = series
                    recreate_data['fragment_number'] = old_data.get('fragment_number', '')
                    model_class.objects.create(**recreate_data)
                    
                elif change.model_type == 'instance':
                    if old_data.get('name'):
                        name = Name.objects.filter(name=old_data['name']).first()
                        if name: recreate_data['name'] = name
                    if old_data.get('fragment'):
                        # Parse fragment string "Series Number"
                        frag_str = old_data['fragment']
                        parts = frag_str.rsplit(' ', 1)
                        if len(parts) == 2:
                            frag = Fragment.objects.filter(
                                series__name=parts[0],
                                fragment_number=parts[1]
                            ).first()
                            if frag: recreate_data['fragment'] = frag
                    recreate_data['line'] = old_data.get('line', '')
                    recreate_data['spelling'] = old_data.get('spelling', '')
                    recreate_data['title_epithet'] = old_data.get('title_epithet', '')
                    if old_data.get('writing_type'):
                        wt = WritingType.objects.filter(name=old_data['writing_type']).first()
                        if wt: recreate_data['writing_type'] = wt
                    if old_data.get('determinative'):
                        det = Determinative.objects.filter(name=old_data['determinative']).first()
                        if det: recreate_data['determinative'] = det
                    model_class.objects.create(**recreate_data)
                    
        elif change.action == 'update':
            # Revert update = restore old values
            if change.old_data and change.object_id:
                try:
                    obj = model_class.objects.get(pk=change.object_id)
                    old_data = change.old_data
                    
                    if change.model_type == 'name':
                        obj.name = old_data.get('name', obj.name)
                        if 'name_type' in old_data:
                            nt = NameType.objects.filter(name=old_data['name_type']).first() if old_data['name_type'] else None
                            obj.name_type = nt
                        if 'writing_type' in old_data:
                            wt = WritingType.objects.filter(name=old_data['writing_type']).first() if old_data['writing_type'] else None
                            obj.writing_type = wt
                        if 'completeness' in old_data:
                            ct = CompletenessType.objects.filter(name=old_data['completeness']).first() if old_data['completeness'] else None
                            obj.completeness = ct
                        if 'milieu' in old_data:
                            m = Milieu.objects.filter(name=old_data['milieu']).first() if old_data['milieu'] else None
                            obj.milieu = m
                        obj.uncertain = old_data.get('uncertain', obj.uncertain)
                        obj.variant_forms = old_data.get('variant_forms', obj.variant_forms)
                        obj.correspondence = old_data.get('correspondence', obj.correspondence)
                        obj.literature = old_data.get('literature', obj.literature)
                        
                    elif change.model_type == 'instance':
                        obj.line = old_data.get('line', obj.line)
                        obj.spelling = old_data.get('spelling', obj.spelling)
                        obj.title_epithet = old_data.get('title_epithet', obj.title_epithet)
                        if 'writing_type' in old_data:
                            wt = WritingType.objects.filter(name=old_data['writing_type']).first() if old_data['writing_type'] else None
                            obj.writing_type = wt
                        if 'determinative' in old_data:
                            det = Determinative.objects.filter(name=old_data['determinative']).first() if old_data['determinative'] else None
                            obj.determinative = det
                            
                    obj.save()
                except model_class.DoesNotExist:
                    return JsonResponse({'error': 'Object no longer exists'}, status=404)
        
        # Mark as reverted
        change.reverted = True
        change.reverted_by = request.user
        change.reverted_at = timezone.now()
        change.save()
        
        return JsonResponse({'success': True})
        
    except ChangeLog.DoesNotExist:
        return JsonResponse({'error': 'Change log not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =============================================================================
# Network API
# =============================================================================

from django.db.models import Count
from collections import defaultdict
import networkx as nx
try:
    import community as community_louvain
    HAS_LOUVAIN = True
except ImportError:
    HAS_LOUVAIN = False

@require_http_methods(["GET"])
def api_network_data(request):
    """
    Get network data for co-occurrence visualization.
    Returns nodes (names) and edges (co-occurrences on same fragments).
    Supports ego network mode for exploring connections of specific names.
    Supports community detection using Louvain algorithm.
    """
    # Get filter parameters
    name_types = request.GET.getlist('name_type')  # List of name type IDs
    series_ids = request.GET.getlist('series')  # List of series IDs
    min_connections = int(request.GET.get('min_connections', 1))
    max_connections = int(request.GET.get('max_connections', 1000))
    min_attestations = int(request.GET.get('min_attestations', 1))
    
    # Community detection parameter
    detect_communities = request.GET.get('communities', 'false').lower() == 'true'
    
    # Ego network parameters - now supports multiple names
    ego_name_ids = request.GET.getlist('ego_name')  # List of selected name IDs
    ego_degree = int(request.GET.get('ego_degree', 1))  # Degree of separation
    
    # Build base fragment filter (by series)
    fragment_filter = {}
    if series_ids:
        fragment_filter['fragment__series_id__in'] = series_ids
    
    # Build queryset for names
    names_qs = Name.objects.all()
    
    if name_types:
        names_qs = names_qs.filter(name_type_id__in=name_types)
    
    # Filter by minimum attestations
    names_qs = names_qs.annotate(
        attestation_count=Count('instances')
    ).filter(attestation_count__gte=min_attestations)
    
    # Get all valid name IDs
    valid_name_ids = set(names_qs.values_list('id', flat=True))
    
    # Build co-occurrence map: for each fragment, which names appear
    fragment_names = defaultdict(set)
    
    instance_qs = Instance.objects.filter(name_id__in=valid_name_ids)
    if fragment_filter:
        instance_qs = instance_qs.filter(**fragment_filter)
    
    instances = instance_qs.values('fragment_id', 'name_id')
    
    for inst in instances:
        if inst['fragment_id']:
            fragment_names[inst['fragment_id']].add(inst['name_id'])
    
    # Count co-occurrences between names
    cooccurrence = defaultdict(int)
    for fragment_id, name_ids in fragment_names.items():
        name_list = list(name_ids)
        for i in range(len(name_list)):
            for j in range(i + 1, len(name_list)):
                # Create sorted tuple for consistent key
                pair = tuple(sorted([name_list[i], name_list[j]]))
                cooccurrence[pair] += 1
    
    # Build adjacency list for ego network expansion
    adjacency = defaultdict(set)
    for (name1, name2) in cooccurrence.keys():
        adjacency[name1].add(name2)
        adjacency[name2].add(name1)
    
    # Count connections per name
    connection_count = defaultdict(int)
    for (name1, name2), count in cooccurrence.items():
        connection_count[name1] += 1
        connection_count[name2] += 1
    
    # Determine which names to include
    if ego_name_ids:
        # Ego network mode: expand from selected names by degree
        ego_name_ids_set = set(int(id) for id in ego_name_ids)
        
        # For ego mode, we need to build adjacency from ALL names (not just filtered)
        # First get all instances for the ego names to find co-occurring names
        all_fragment_names = defaultdict(set)
        all_instance_qs = Instance.objects.all()
        if series_ids:
            all_instance_qs = all_instance_qs.filter(fragment__series_id__in=series_ids)
        
        for inst in all_instance_qs.values('fragment_id', 'name_id'):
            if inst['fragment_id'] and inst['name_id']:
                all_fragment_names[inst['fragment_id']].add(inst['name_id'])
        
        # Build full adjacency
        full_adjacency = defaultdict(set)
        for fragment_id, name_ids in all_fragment_names.items():
            name_list = list(name_ids)
            for i in range(len(name_list)):
                for j in range(i + 1, len(name_list)):
                    full_adjacency[name_list[i]].add(name_list[j])
                    full_adjacency[name_list[j]].add(name_list[i])
        
        # Expand from all ego names by degree
        ego_names = set(ego_name_ids_set)
        current_frontier = set(ego_name_ids_set)
        
        for d in range(ego_degree):
            next_frontier = set()
            for name_id in current_frontier:
                next_frontier.update(full_adjacency.get(name_id, set()))
            ego_names.update(next_frontier)
            current_frontier = next_frontier - ego_names
        
        filtered_name_ids = ego_names
        
        # Recalculate connection counts for ego network
        connection_count = defaultdict(int)
        for name_id in filtered_name_ids:
            connection_count[name_id] = len(full_adjacency.get(name_id, set()) & filtered_name_ids)
        
        # Rebuild cooccurrence for edges within ego network
        cooccurrence = defaultdict(int)
        for fragment_id, name_ids in all_fragment_names.items():
            relevant = name_ids & filtered_name_ids
            relevant_list = list(relevant)
            for i in range(len(relevant_list)):
                for j in range(i + 1, len(relevant_list)):
                    pair = tuple(sorted([relevant_list[i], relevant_list[j]]))
                    cooccurrence[pair] += 1
    else:
        # Standard mode: filter by connection count
        filtered_name_ids = {
            name_id for name_id, count in connection_count.items()
            if min_connections <= count <= max_connections
        }
        
        # If no connections filter applied (min=0), include isolated nodes
        if min_connections == 0:
            filtered_name_ids.update(valid_name_ids)
        
        # No ego names in global mode
        ego_name_ids_set = set()
    
    # Community detection using Louvain algorithm
    communities = {}
    num_communities = 0
    if detect_communities and HAS_LOUVAIN and len(filtered_name_ids) > 1:
        # Build networkx graph
        G = nx.Graph()
        G.add_nodes_from(filtered_name_ids)
        for (name1, name2), weight in cooccurrence.items():
            if name1 in filtered_name_ids and name2 in filtered_name_ids:
                G.add_edge(name1, name2, weight=weight)
        
        # Run Louvain community detection
        if G.number_of_edges() > 0:
            partition = community_louvain.best_partition(G, weight='weight', resolution=1.0)
            communities = partition
            num_communities = len(set(partition.values()))
    
    # Get name details for filtered names
    names_data = Name.objects.filter(
        id__in=filtered_name_ids
    ).select_related('name_type').annotate(
        attestation_count=Count('instances')
    )
    
    # Build nodes
    nodes = []
    for name in names_data:
        node = {
            'id': name.id,
            'name': name.name,
            'name_type': name.name_type.name if name.name_type else 'Unknown',
            'attestations': name.attestation_count,
            'connections': connection_count.get(name.id, 0),
        }
        # Mark the ego nodes (can be multiple now)
        if name.id in ego_name_ids_set:
            node['is_ego'] = True
        # Add community ID if available
        if name.id in communities:
            node['community'] = communities[name.id]
        nodes.append(node)
    
    # Build edges (only between filtered names)
    edges = []
    for (name1, name2), weight in cooccurrence.items():
        if name1 in filtered_name_ids and name2 in filtered_name_ids:
            edges.append({
                'source': name1,
                'target': name2,
                'weight': weight,
            })
    
    return JsonResponse({
        'nodes': nodes,
        'edges': edges,
        'stats': {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'num_communities': num_communities,
        }
    })


@require_http_methods(["GET"])
def api_name_search(request):
    """Search names for autocomplete in network page"""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})
    
    names = Name.objects.filter(
        Q(name__icontains=q) | Q(query__icontains=q)
    ).select_related('name_type')[:20]
    
    results = [{
        'id': n.id,
        'name': n.name,
        'name_type': n.name_type.name if n.name_type else 'Unknown',
    } for n in names]
    
    return JsonResponse({'results': results})
