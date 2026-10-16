from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model

from .serializers import (
    UserRegistrationSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
)
from .permissions import IsAdminOrSelf

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Register a new user (any role). No authentication required.
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/auth/profile/   — view your own profile
    PATCH /api/auth/profile/  — update your own profile
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    Change logged-in user's password.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response(
                {'detail': 'Password changed successfully.'},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(generics.ListAPIView):
    """
    GET /api/users/
    List all users — admin only.
    """
    queryset = User.objects.all().order_by('date_joined')
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only admins can list all users; others see only themselves
        if self.request.user.role == 'admin':
            return User.objects.all().order_by('date_joined')
        return User.objects.filter(pk=self.request.user.pk)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/users/<pk>/  — retrieve a user
    PATCH  /api/users/<pk>/  — update a user (admin or self)
    DELETE /api/users/<pk>/  — delete a user (admin only)
    """
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSelf]
