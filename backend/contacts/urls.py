from django.urls import path
from . import views

urlpatterns = [
    # Emergency contacts CRUD
    path('', views.EmergencyContactListCreateView.as_view(), name='contact-list'),
    path('<int:pk>/', views.EmergencyContactDetailView.as_view(), name='contact-detail'),

    # Verification
    path('<int:pk>/verify/', views.ContactVerifyView.as_view(), name='contact-verify'),
    path(
        '<int:pk>/resend-verification/',
        views.ResendVerificationView.as_view(),
        name='contact-resend-verification',
    ),
]
