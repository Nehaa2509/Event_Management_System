import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Sum

MAX_TICKETS_PER_USER = 5

class Event(models.Model):
    CATEGORY_CHOICES = [
        ('CONFERENCE', 'Conference'),
        ('WORKSHOP', 'Workshop'),
        ('MEETUP', 'Meetup'),
        ('HACKATHON', 'Hackathon'),
        ('WEBINAR', 'Webinar'),
        ('OTHER', 'Other'),
    ]

    EVENT_TYPE_CHOICES = [
        ('IN_PERSON', 'In-Person'),
        ('VIRTUAL', 'Virtual'),
        ('HYBRID', 'Hybrid'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    date = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='IN_PERSON')
    speaker_name = models.CharField(max_length=150, blank=True, default='')
    speaker_role = models.CharField(max_length=150, blank=True, default='')
    image = models.ImageField(upload_to='event_banners/', blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def total_booked_tickets(self):
        return self.registrations.aggregate(total=Sum('quantity'))['total'] or 0

    @property
    def slots_left(self):
        return max(0, self.capacity - self.total_booked_tickets)

class Registration(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registrations')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    quantity = models.PositiveIntegerField(default=1)
    ticket_code = models.CharField(max_length=20, unique=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'event'], name='unique_user_event_registration')
        ]

    def clean(self):
        if self.quantity < 1:
            raise ValidationError("Quantity must be at least 1 ticket.")
        if self.quantity > MAX_TICKETS_PER_USER:
            raise ValidationError(f"Cannot book more than {MAX_TICKETS_PER_USER} tickets per user.")

    def save(self, *args, **kwargs):
        if not self.ticket_code:
            self.ticket_code = f"TIC-{uuid.uuid4().hex[:8].upper()}"
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} ({self.ticket_code}) - {self.quantity} ticket(s) for {self.event.title}"

class ContactInquiry(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Contact Inquiries"

    def __str__(self):
        return f"Inquiry from {self.name} ({self.email})"
