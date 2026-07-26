from django.db import transaction, OperationalError
from django.db.models import Sum
from .models import Event, Registration, MAX_TICKETS_PER_USER


class RegistrationError(Exception):
    """Custom exception raised when registration fails due to business rules."""
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def register_user_for_event(user, event_id, quantity=1):
    """
    Safely registers a user (or updates existing registration) for an event with ticket quantity,
    using database row locking (select_for_update) and atomic transaction.
    Enforces MAX_TICKETS_PER_USER (5) and event capacity constraints.
    Raises RegistrationError or Event.DoesNotExist.
    """
    try:
        qty = int(quantity)
        if qty < 1:
            raise RegistrationError("Ticket quantity must be at least 1.", status_code=400)
    except (ValueError, TypeError):
        raise RegistrationError("Invalid quantity specified.", status_code=400)

    try:
        with transaction.atomic():
            event = Event.objects.select_for_update().get(id=event_id)

            if not event.is_approved:
                raise RegistrationError("Cannot register for an unapproved event.", status_code=400)

            # Check existing user registration for this event
            existing_reg = Registration.objects.filter(user=user, event=event).first()
            existing_qty = existing_reg.quantity if existing_reg else 0

            # Max limit check per user (5 total tickets allowed per user)
            if existing_qty + qty > MAX_TICKETS_PER_USER:
                remaining_user_allowance = max(0, MAX_TICKETS_PER_USER - existing_qty)
                if remaining_user_allowance == 0:
                    raise RegistrationError(
                        f"You have already reached the maximum limit of {MAX_TICKETS_PER_USER} tickets for this event.",
                        status_code=400
                    )
                else:
                    raise RegistrationError(
                        f"Maximum limit is {MAX_TICKETS_PER_USER} tickets per user. You currently hold {existing_qty} ticket(s), so you can only add up to {remaining_user_allowance} more.",
                        status_code=400
                    )

            if existing_reg:
                existing_qty = existing_reg.quantity
                if existing_qty + qty > MAX_TICKETS_PER_USER:
                    remaining_user_allowance = max(0, MAX_TICKETS_PER_USER - existing_qty)
                    if remaining_user_allowance == 0:
                        raise RegistrationError(
                            f"You are already registered for the maximum limit of {MAX_TICKETS_PER_USER} tickets for this event.",
                            status_code=400
                        )
                    else:
                        raise RegistrationError(
                            f"Maximum limit is {MAX_TICKETS_PER_USER} tickets per user. You currently hold {existing_qty} ticket(s), so you can only add up to {remaining_user_allowance} more.",
                            status_code=400
                        )

                total_booked = event.registrations.aggregate(total=Sum('quantity'))['total'] or 0
                available_seats = max(0, event.capacity - total_booked)

                if available_seats <= 0:
                    raise RegistrationError("You are already registered for this event, and it is fully booked!", status_code=400)

                if qty > available_seats:
                    raise RegistrationError(
                        f"Only {available_seats} available seat(s) remaining for this event.",
                        status_code=400
                    )

                existing_reg.quantity += qty
                existing_reg.save()
                existing_reg.is_new = False
                return existing_reg

            # New registration
            total_booked = event.registrations.aggregate(total=Sum('quantity'))['total'] or 0
            available_seats = max(0, event.capacity - total_booked)

            if available_seats <= 0:
                raise RegistrationError("Event is fully booked!", status_code=400)

            if qty > available_seats:
                raise RegistrationError(
                    f"Only {available_seats} available seat(s) remaining for this event.",
                    status_code=400
                )

            registration = Registration.objects.create(user=user, event=event, quantity=qty)
            registration.is_new = True
            return registration

    except OperationalError:
        raise RegistrationError("Database busy, please try again.", status_code=503)
