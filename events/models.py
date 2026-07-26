import uuid
from django.db import models
from django.contrib.auth.models import User

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
    def slots_left(self):
        return max(0, self.capacity - self.registrations.count())

class Registration(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registrations')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    ticket_code = models.CharField(max_length=20, unique=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'event'], name='unique_user_event_registration')
        ]

    def save(self, *args, **kwargs):
        if not self.ticket_code:
            self.ticket_code = f"TIC-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} ({self.ticket_code}) registered for {self.event.title}"

