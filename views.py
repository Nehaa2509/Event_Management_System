from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from .models import Event, Registration
from django.utils import timezone
from datetime import datetime

def register_user(request):
    if request.user.is_authenticated:
        return redirect('event_list')
        
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not username or not password:
            messages.error(request, "Username and password are required.")
            return render(request, 'events/register.html')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'events/register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
            return render(request, 'events/register.html')

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            messages.success(request, f"Welcome, {username}! Your account has been created.")
            return redirect('event_list')
        except Exception as e:
            messages.error(request, "An error occurred during registration. Please try again.")
            return render(request, 'events/register.html')

    return render(request, 'events/register.html')

def login_user(request):
    if request.user.is_authenticated:
        return redirect('event_list')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {username}!")
            return redirect('event_list')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'events/login.html')

def logout_user(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')

def event_list(request):
    query = request.GET.get('q', '').strip()
    location_filter = request.GET.get('location', '').strip()
    date_filter = request.GET.get('date', '').strip()
    
    events = Event.objects.filter(is_approved=True)
    
    if query:
        events = events.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )
        
    if location_filter:
        events = events.filter(location__icontains=location_filter)
        
    if date_filter:
        try:
            parsed_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            events = events.filter(date__date=parsed_date)
        except ValueError:
            pass
            
    # Get distinct locations for the sidebar filter
    locations = Event.objects.filter(is_approved=True).values_list('location', flat=True).distinct()
    
    context = {
        'events': events.order_by('date'),
        'query': query,
        'location_filter': location_filter,
        'date_filter': date_filter,
        'locations': locations,
    }
    return render(request, 'events/event_list.html', context)

@login_required
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    
    # Non-staff cannot see unapproved events unless they organized it
    if not event.is_approved and not request.user.is_staff and event.organizer != request.user:
        raise PermissionDenied("You do not have permission to view this pending event.")
        
    already_registered = Registration.objects.filter(user=request.user, event=event).exists()
    registrations_count = event.registrations.count()
    slots_left = max(0, event.capacity - registrations_count)
    
    context = {
        'event': event,
        'already_registered': already_registered,
        'registrations_count': registrations_count,
        'slots_left': slots_left,
    }
    return render(request, 'events/event_detail.html', context)

@login_required
def create_event(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        location = request.POST.get('location', '').strip()
        date_str = request.POST.get('date', '').strip()
        capacity = request.POST.get('capacity', '').strip()

        if not (title and description and location and date_str and capacity):
            messages.error(request, "All fields are required.")
            return render(request, 'events/create_event.html')

        try:
            capacity_val = int(capacity)
            if capacity_val <= 0:
                raise ValueError()
        except ValueError:
            messages.error(request, "Capacity must be a positive number.")
            return render(request, 'events/create_event.html')

        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            # Make timezone aware if settings.USE_TZ is True
            event_date = timezone.make_aware(event_date)
        except ValueError:
            messages.error(request, "Invalid date format.")
            return render(request, 'events/create_event.html')

        event = Event.objects.create(
            title=title,
            description=description,
            location=location,
            date=event_date,
            capacity=capacity_val,
            organizer=request.user,
            is_approved=False # Requires admin approval
        )
        
        messages.success(request, f"Event '{title}' created successfully! It will be visible once approved by an administrator.")
        return redirect('event_list')

    return render(request, 'events/create_event.html')

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        raise PermissionDenied("Only administrators can access the dashboard.")
        
    pending_events = Event.objects.filter(is_approved=False).order_by('-created_at')
    approved_events = Event.objects.filter(is_approved=True).order_by('-created_at')
    
    context = {
        'pending_events': pending_events,
        'approved_events': approved_events,
    }
    return render(request, 'events/admin_dashboard.html', context)

@login_required
def approve_event_view(request, event_id):
    # Quick RBAC Check using Django's built-in admin/staff flag
    if not request.user.is_staff:
        raise PermissionDenied("Only administrators can approve events.")
        
    if request.method == 'POST':
        event = get_object_or_404(Event, id=event_id)
        event.is_approved = True
        event.save()
        messages.success(request, f"Event '{event.title}' has been successfully approved.")
        return redirect('admin_dashboard')
        
    return redirect('admin_dashboard')

@login_required
def register_for_event(request, event_id):
    user = request.user
    
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
        
    try:
        # 'select_for_update' locks the event row during the transaction block
        with transaction.atomic():
            event = Event.objects.select_for_update().get(id=event_id)
            
            # Check if event is approved
            if not event.is_approved:
                return JsonResponse({"error": "Cannot register for an unapproved event."}, status=400)
                
            # 1. Check current registrations against capacity
            current_registrations_count = event.registrations.count()
            
            if current_registrations_count >= event.capacity:
                return JsonResponse({"error": "Event is fully booked!"}, status=400)
            
            # 2. Check if already registered
            if Registration.objects.filter(user=user, event=event).exists():
                return JsonResponse({"error": "You are already registered."}, status=400)
                
            # 3. Safely create registration
            Registration.objects.create(user=user, event=event)
            
            return JsonResponse({"message": "Successfully registered!"}, status=201)
            
    except Event.DoesNotExist:
        return JsonResponse({"error": "Event not found"}, status=404)
