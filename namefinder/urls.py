from django.urls import path
from . import views
from . import api_views

app_name = 'namefinder'

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('name/<int:pk>/', views.name_detail, name='name_detail'),
    path('fragments/', views.fragment_search, name='fragment_search'),
    path('fragment/<int:pk>/', views.fragment_detail, name='fragment_detail'),
    path('about/', views.about, name='about'),
    
    # Authentication
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # CSV exports
    path('export/search/', views.export_search_csv, name='export_search_csv'),
    path('export/name/<int:pk>/', views.export_name_csv, name='export_name_csv'),
    path('export/fragment/<int:pk>/', views.export_fragment_csv, name='export_fragment_csv'),
    
    # Name CRUD (form-based)
    path('name/create/', views.name_create, name='name_create'),
    path('name/<int:pk>/edit/', views.name_edit, name='name_edit'),
    path('name/<int:pk>/delete/', views.name_delete, name='name_delete'),
    
    # Fragment CRUD (form-based)
    path('fragment/create/', views.fragment_create, name='fragment_create'),
    path('fragment/<int:pk>/edit/', views.fragment_edit, name='fragment_edit'),
    path('fragment/<int:pk>/delete/', views.fragment_delete, name='fragment_delete'),
    
    # Instance (Attestation) CRUD (form-based)
    path('instance/create/', views.instance_create, name='instance_create'),
    path('instance/<int:pk>/edit/', views.instance_edit, name='instance_edit'),
    path('instance/<int:pk>/delete/', views.instance_delete, name='instance_delete'),
    
    # API endpoints for inline editing (AJAX)
    path('api/name/<int:pk>/', api_views.api_name_update, name='api_name_update'),
    path('api/name/<int:pk>/delete/', api_views.api_name_delete, name='api_name_delete'),
    path('api/instance/', api_views.api_instance_create, name='api_instance_create'),
    path('api/instance/<int:pk>/', api_views.api_instance_update, name='api_instance_update'),
    path('api/instance/<int:pk>/delete/', api_views.api_instance_delete, name='api_instance_delete'),
    path('api/fragment/<int:pk>/', api_views.api_fragment_update, name='api_fragment_update'),
    path('api/fragment/<int:pk>/delete/', api_views.api_fragment_delete, name='api_fragment_delete'),
    path('api/fragment/search/', api_views.api_fragment_search, name='api_fragment_search'),
    path('api/fragment/create/', api_views.api_fragment_create, name='api_fragment_create'),
    path('api/revert/<int:pk>/', api_views.api_revert_change, name='api_revert_change'),
    path('api/network/', api_views.api_network_data, name='api_network_data'),
    path('api/name/search/', api_views.api_name_search, name='api_name_search'),
    
    # Network visualization
    path('network/', views.network, name='network'),
    
    # Changes log (admin only)
    path('changes/', views.changes, name='changes'),
]
