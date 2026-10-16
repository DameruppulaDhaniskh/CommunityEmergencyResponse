from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # User auth & management
    path('api/', include('users.urls')),

    # Society management: /api/society/...
    path('api/society/', include('society.urls')),

    # Emergency contacts: /api/contacts/...
    path('api/contacts/', include('contacts.urls')),
]