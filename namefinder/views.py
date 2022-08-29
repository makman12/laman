from django.shortcuts import render
from django.http import HttpResponse, JsonResponse

from namefinder import serializers

# Create your views here.

def index(request):
    return render(request, 'namefinder/index.html')

def help(request):
    return render(request, 'namefinder/help.html')



from .serializers import NameSerializer, InstanceSerializer
from rest_framework.decorators import api_view
from .models import Name,Instance


@api_view(['GET'])
def get_detail(request, name_id):
    try:
        name = Name.objects.get(pk=name_id)
        instances = name.instance_set.all()

    except Name.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'GET':
        serializer = NameSerializer(name)
        return JsonResponse({'name': serializer.data, 'instances': InstanceSerializer(instances, many=True).data})

@api_view(['GET'])
def query_regex(request,query):
    # appyl regex to query and return all names that match
    try:
        names = Name.objects.filter(query__regex=query)
        # return just ids of names as a json list
        names_ids = [name.name_id for name in names]
        return JsonResponse(names_ids, safe=False)
    except Name.DoesNotExist:
        return HttpResponse(status=404)

@api_view(['GET'])
def get_tag(request, name_id):
    try:
        name = Name.objects.get(pk=name_id)

    except Name.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'GET':
        serializer = NameSerializer.Tag(name)
        return JsonResponse(serializer.data)

@api_view(['GET'])
def get_tags(request, count):
    try:
        # get 100 names
        names = Name.objects.all()[:count]
    except Name.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'GET':
       serializers = NameSerializer.Tag(names, many=True)
       return JsonResponse(serializers.data, safe=False) 

from django.views.decorators.csrf import csrf_exempt

@api_view(['POST'])
@csrf_exempt
def search(request):
    print("geldi")
    # e.g {"query": ".*", "regex": true, "type": "person", "completeness": "complete", "writing": "sumerogram"}
    data = request.data
    print(data)
    query = data['query']
    regex = data['regex']
    if regex:
        names = Name.objects.filter(query__regex=query)
    else:
        # if regex is false, then search for query as a substring
        names= Name.objects.filter(query__icontains=query)
    if data['type']!="all":
        names = names.filter(type=data['type'])
    if data['comp']!="all":
        names = names.filter(completeness=data['comp'])
    if data['spel']!="all":
        names = names.filter(writing_clean=data['spel'])
    serializer = NameSerializer.Tag(names, many=True)
    return JsonResponse(serializer.data, safe=False)
