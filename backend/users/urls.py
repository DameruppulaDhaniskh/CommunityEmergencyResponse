from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)
from . import views

urlpatterns = [
    # ---------- Auth ----------
    path('auth/register/', views.RegisterView.as_view(), name='auth-register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='auth-login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('auth/logout/', TokenBlacklistView.as_view(), name='auth-logout'),
    path('auth/profile/', views.UserProfileView.as_view(), name='auth-profile'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='auth-change-password'),

    # ---------- Admin user management ----------
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
]
