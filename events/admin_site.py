"""
Custom AdminSite that injects event moderation data into the dashboard index.
Models are registered on `wiwi_admin_site` in events/admin.py via default_auto_field.
"""
from django.contrib.admin import AdminSite
from .models import Event


class WiwiAdminSite(AdminSite):
    site_header = "Wiwi Events Administration"
    site_title  = "Wiwi Events Admin Portal"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['pending_events']  = (
            Event.objects.filter(is_approved=False).order_by('-created_at')
        )
        extra_context['approved_events'] = (
            Event.objects.filter(is_approved=True).order_by('-created_at')
        )
        return super().index(request, extra_context=extra_context)


wiwi_admin_site = WiwiAdminSite(name='admin')
