from django.urls import path
from . import views

urlpatterns = [
    # Society
    path('', views.SocietyListCreateView.as_view(), name='society-list'),
    path('<int:pk>/', views.SocietyDetailView.as_view(), name='society-detail'),

    # Blocks under a society
    path('<int:society_pk>/blocks/', views.BlockListCreateView.as_view(), name='block-list'),

    # Blocks (direct access)
    path('blocks/<int:pk>/', views.BlockDetailView.as_view(), name='block-detail'),

    # Flats under a block
    path('blocks/<int:block_pk>/flats/', views.FlatListCreateView.as_view(), name='flat-list'),

    # Flats (direct access)
    path('flats/<int:pk>/', views.FlatDetailView.as_view(), name='flat-detail'),

    # Resident-flat mappings
    path('mappings/', views.ResidentFlatMappingListCreateView.as_view(), name='mapping-list'),
    path('mappings/<int:pk>/', views.ResidentFlatMappingDetailView.as_view(), name='mapping-detail'),
]
