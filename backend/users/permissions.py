from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Allow access only to users with role='admin'."""
    message = 'Only society admins can perform this action.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )


class IsSecurityPersonnel(BasePermission):
    """Allow access only to users with role='security'."""
    message = 'Only security personnel can perform this action.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'security'
        )


class IsVolunteer(BasePermission):
    """Allow access only to users with role='volunteer'."""
    message = 'Only volunteers can perform this action.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'volunteer'
        )


class IsGuardian(BasePermission):
    """Allow access only to users with role='guardian'."""
    message = 'Only guardians can perform this action.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'guardian'
        )


class IsAdminOrSelf(BasePermission):
    """
    Allow access to:
    - Society admins (full access).
    - The user themselves (can only access their own record).
    """
    message = 'You do not have permission to access this resource.'

    def has_object_permission(self, request, view, obj):
        return (
            request.user.role == 'admin'
            or obj == request.user
        )


class IsAdminOrReadOnly(BasePermission):
    """
    Read-only for any authenticated user.
    Write access only for admins.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.role == 'admin'
