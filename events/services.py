from django.db import transaction, OperationalError
from .models import Event, Registration


class RegistrationError(Exception):
    """Custom exception raised when registration fails due to business rules."""
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def register_user_for_event(user, event_id):
    """
    Safely registers a user for an event using database row locking (select_for_update)
    and atomic transaction to prevent race conditions / double-booking.
    Raises RegistrationError or Event.DoesNotExist.
    """
    try:
        with transaction.atomic():
            event = Event.objects.select_for_update().get(id=event_id)

            if not event.is_approved:
                raise RegistrationError("Cannot register for an unapproved event.", status_code=400)

            if Registration.objects.filter(user=user, event=event).exists():
                raise RegistrationError("You are already registered.", status_code=400)

            current_registrations_count = event.registrations.count()

            if current_registrations_count >= event.capacity:
                raise RegistrationError("Event is fully booked!", status_code=400)

            registration = Registration.objects.create(user=user, event=event)
            return registration

    except OperationalError:
        raise RegistrationError("Database busy, please try again.", status_code=503)
