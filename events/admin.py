from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
from django.utils.html import format_html
from .admin_site import wiwi_admin_site
from .models import Event, Registration, ContactInquiry

# ---------------------------------------------------------------------------
# Admin site global branding (also applied to default site as fallback)
# ---------------------------------------------------------------------------
admin.site.site_header = "Wiwi Events Administration"
admin.site.site_title  = "Wiwi Events Admin Portal"
admin.site.index_title = "Dashboard"


# ---------------------------------------------------------------------------
# Custom admin actions
# ---------------------------------------------------------------------------

@admin.action(description="✅ Approve selected events")
def approve_selected_events(modeladmin, request, queryset):
    updated = queryset.update(is_approved=True)
    modeladmin.message_user(
        request,
        f"{updated} event(s) were successfully approved.",
    )


@admin.action(description="❌ Reject & delete selected unapproved events")
def reject_selected_events(modeladmin, request, queryset):
    """
    Only deletes events that are NOT approved, so accidental selection of
    live events is safe — they are silently skipped.
    """
    unapproved_qs = queryset.filter(is_approved=False)
    count = unapproved_qs.count()
    unapproved_qs.delete()
    modeladmin.message_user(
        request,
        f"{count} unapproved event(s) were deleted. "
        f"Already-approved events in the selection were left untouched.",
    )


# ---------------------------------------------------------------------------
# Inline: Attendees list embedded in the Event detail page
# ---------------------------------------------------------------------------

class RegistrationInline(admin.TabularInline):
    model = Registration
    fields = ("user", "ticket_code", "registered_at")
    readonly_fields = ("user", "ticket_code", "registered_at")
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = "Attendee"
    verbose_name_plural = "Attendees"


# ---------------------------------------------------------------------------
# EventAdmin
# ---------------------------------------------------------------------------

class EventAdmin(ModelAdmin):
    # ---- List view --------------------------------------------------------
    list_display = (
        "image_thumbnail",
        "title",
        "category",
        "event_type",
        "date",
        "location",
        "organizer",
        "is_approved",
        "slots_left_display",
    )
    list_filter = ("category", "event_type", "is_approved", "date")
    search_fields = ("title", "description", "location", "speaker_name")
    list_editable = ("is_approved",)
    date_hierarchy = "date"
    ordering = ("-created_at",)

    # ---- Detail view ------------------------------------------------------
    readonly_fields = ("created_at", "slots_left_display", "image_thumbnail")
    autocomplete_fields = ["organizer"]
    inlines = [RegistrationInline]

    # ---- Actions ----------------------------------------------------------
    actions = [approve_selected_events, reject_selected_events]

    list_per_page = 25

    @admin.display(description="Slots Left", ordering="capacity")
    def slots_left_display(self, obj):
        return obj.slots_left

    @admin.display(description="Banner")
    def image_thumbnail(self, obj):
        if obj and getattr(obj, 'image', None):
            return format_html(
                '<img src="{}" style="height:50px; width:80px; object-fit:cover; border-radius:6px;">',
                obj.image.url,
            )
        return format_html('<span style="color:#64748b;">{}</span>', '—')


# ---------------------------------------------------------------------------
# RegistrationAdmin
# ---------------------------------------------------------------------------

class RegistrationAdmin(ModelAdmin):
    list_display = ("user", "event", "ticket_code", "registered_at")
    list_filter = ("registered_at", "event")
    search_fields = (
        "user__username",
        "user__email",
        "event__title",
        "ticket_code",
    )
    readonly_fields = ("ticket_code", "registered_at")
    autocomplete_fields = ["user", "event"]
    ordering = ("-registered_at",)
    list_per_page = 25


# ---------------------------------------------------------------------------
# Register on the custom Wiwi admin site
# ---------------------------------------------------------------------------
wiwi_admin_site.register(Event, EventAdmin)
wiwi_admin_site.register(Registration, RegistrationAdmin)
# User & Group are required so autocomplete_fields work on this custom site
wiwi_admin_site.register(User, UserAdmin)
wiwi_admin_site.register(Group, GroupAdmin)

# Also register on default admin site so Django's auto-wiring works
try:
    admin.site.register(Event, EventAdmin)
    admin.site.register(Registration, RegistrationAdmin)
except admin.sites.AlreadyRegistered:
    pass

@admin.register(ContactInquiry)
class ContactInquiryAdmin(ModelAdmin):
    list_display = ('name', 'email', 'created_at')
    readonly_fields = ('name', 'email', 'message', 'created_at')
    ordering = ('-created_at',)

wiwi_admin_site.register(ContactInquiry, ContactInquiryAdmin)
