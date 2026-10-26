from django.urls import path
from . import views

urlpatterns = [
    path('', views.IncidentListView.as_view(), name='incident-list'),
    path('sos/', views.SOSCreateView.as_view(), name='incident-sos'),
    path('<int:pk>/', views.IncidentDetailView.as_view(), name='incident-detail'),
    path('<int:pk>/status/', views.IncidentStatusView.as_view(), name='incident-status'),
]