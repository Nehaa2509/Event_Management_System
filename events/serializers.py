from rest_framework import serializers
from .models import Event, Registration


class EventSerializer(serializers.ModelSerializer):
    slots_left = serializers.IntegerField(read_only=True)
    organizer_username = serializers.CharField(source='organizer.username', read_only=True)

    class Meta:
        model = Event
        fields = [
            'id',
            'title',
            'description',
            'location',
            'date',
            'capacity',
            'category',
            'event_type',
            'speaker_name',
            'speaker_role',
            'image',
            'is_approved',
            'organizer',
            'organizer_username',
            'slots_left',
            'created_at',
        ]
        read_only_fields = ['id', 'is_approved', 'organizer', 'created_at']


class EventCreateSerializer(serializers.ModelSerializer):
    slots_left = serializers.IntegerField(read_only=True)

    class Meta:
        model = Event
        fields = [
            'id',
            'title',
            'description',
            'location',
            'date',
            'capacity',
            'category',
            'event_type',
            'speaker_name',
            'speaker_role',
            'image',
            'slots_left',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class RegistrationSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    ticket_code = serializers.CharField(read_only=True)
    registered_at = serializers.DateTimeField(read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Registration
        fields = [
            'id',
            'user',
            'user_username',
            'event',
            'event_title',
            'ticket_code',
            'registered_at',
        ]
        read_only_fields = ['id', 'user', 'ticket_code', 'registered_at']
