"""
URL configuration for the wiwievents project.
"""
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from events.admin_site import wiwi_admin_site
from django.http import HttpResponse
from django.contrib.auth.models import User

def create_admin(request):
    u, created = User.objects.get_or_create(username='sneha')
    u.is_staff = True
    u.is_superuser = True
    u.set_password('admin123')
    u.save()
    return HttpResponse("SUCCESS! The user 'sneha' is now a superuser. You can log into the admin page with password 'admin123'.")

urlpatterns = [
    path('admin/', wiwi_admin_site.urls),
    path('setup-admin-999/', create_admin),
    path('api/v1/', include('events.api_urls')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('', include('events.urls')),
]

import os

# Serve uploaded media files during development ONLY if Cloudinary is not configured
if settings.DEBUG and not os.environ.get('CLOUDINARY_CLOUD_NAME'):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
