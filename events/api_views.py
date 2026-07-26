from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from .models import Event, Registration
from .serializers import EventSerializer, EventCreateSerializer, RegistrationSerializer
from .services import register_user_for_event, RegistrationError


class IsOrganizerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow organizers of an event or staff members to edit/delete it.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff or obj.organizer == request.user


class IsRegistrationOwnerOrStaff(permissions.BasePermission):
    """
    Custom permission to only allow registration owner or staff to view/delete registrations.
    """
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.user == request.user


class EventViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Events.
    - Anonymous/non-owner users see only approved events.
    - Organizers see approved events + their own unapproved events.
    - Staff members see all events.
    - Supports filtering by category, event_type, upcoming=true, and search on text fields.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOrganizerOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description', 'location', 'speaker_name']

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            queryset = Event.objects.all()
        elif user.is_authenticated:
            queryset = Event.objects.filter(Q(is_approved=True) | Q(organizer=user))
        else:
            queryset = Event.objects.filter(is_approved=True)

        # Filtering options
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        event_type = self.request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)

        upcoming = self.request.query_params.get('upcoming')
        if upcoming and upcoming.lower() in ['true', '1', 'yes']:
            queryset = queryset.filter(date__gte=timezone.now())

        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return EventCreateSerializer
        return EventSerializer

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user, is_approved=False)


class RegistrationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Registrations.
    - Non-staff users only see their own registrations.
    - Creating a registration re-uses thread-safe capacity checking logic.
    - Cancelling (delete) is allowed for registration owners or staff.
    """
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.IsAuthenticated, IsRegistrationOwnerOrStaff]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Registration.objects.none()
        if user.is_staff:
            return Registration.objects.all().order_by('-registered_at')
        return Registration.objects.filter(user=user).order_by('-registered_at')

    def create(self, request, *args, **kwargs):
        event_id = request.data.get('event')
        if not event_id:
            return Response(
                {"event": ["This field is required. Provide the 'event' ID."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            registration = register_user_for_event(user=request.user, event_id=event_id)
            serializer = self.get_serializer(registration)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except RegistrationError as e:
            return Response({"detail": e.message}, status=status.HTTP_400_BAD_REQUEST)
        except Event.DoesNotExist:
            return Response({"detail": "Event not found."}, status=status.HTTP_404_NOT_FOUND)
