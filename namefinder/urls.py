from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('help/', views.help, name='help'),
    path('api/detail/<int:name_id>/', views.get_detail, name='get_detail'),
    path('api/query/<str:query>/', views.query_regex, name='query_regex'),
    path('api/tag/<int:name_id>/', views.get_tag, name='get_tag'),
    path('api/tags/<int:count>/', views.get_tags, name='get_tags'),
    path('api/search/', views.search, name='search'),
]
