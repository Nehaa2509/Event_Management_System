"""
URL configuration for the wiwievents project.
"""
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from events.admin_site import wiwi_admin_site

urlpatterns = [
    path('admin/', wiwi_admin_site.urls),
    path('api/v1/', include('events.api_urls')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('', include('events.urls')),
]

import os

# Serve uploaded media files during development ONLY if Cloudinary is not configured
if settings.DEBUG and not os.environ.get('CLOUDINARY_CLOUD_NAME'):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
