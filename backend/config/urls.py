from django.contrib import admin
from django.urls import path, include
from incidents.views import ResidentIncidentListView
from notifications.views import IncidentNotificationListView, IncidentNotificationRetryView
urlpatterns = [
    path('admin/', admin.site.urls),

    # User auth & management
    path('api/', include('users.urls')),

    # Society management: /api/society/...
    path('api/society/', include('society.urls')),

    # Emergency contacts: /api/contacts/...
    path('api/contacts/', include('contacts.urls')),

    path('api/incidents/', include('incidents.urls')),
    path('api/resident/incidents/', ResidentIncidentListView.as_view(), name='resident-incidents'),
    path('api/notifications/', include('notifications.urls')),
    path('api/incidents/<int:pk>/notifications/', IncidentNotificationListView.as_view(), name='incident-notifications'),
    path('api/incidents/<int:pk>/notifications/retry/', IncidentNotificationRetryView.as_view(), name='incident-notifications-retry'),
]