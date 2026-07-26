from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction, IntegrityError, OperationalError
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from .models import Event, Registration
from .services import register_user_for_event, RegistrationError
from django.utils import timezone
import logging
from datetime import datetime, timedelta
import qrcode
from qrcode.image.pil import PilImage
import io
import base64

logger = logging.getLogger(__name__)

def parse_event_date(date_str):
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            dt = datetime.strptime(date_str, fmt)
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            return dt
        except ValueError:
            continue
    return None

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

        # Run Django built-in password validators
        try:
            validate_password(password)
        except ValidationError as e:
            for err_msg in e.messages:
                messages.error(request, err_msg)
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
    category_filter = request.GET.get('category', '').strip()
    event_type_filter = request.GET.get('event_type', '').strip()
    
    events = Event.objects.filter(is_approved=True)
    
    if query:
        events = events.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(speaker_name__icontains=query)
        )
        
    if location_filter:
        events = events.filter(location__icontains=location_filter)
        
    if category_filter:
        events = events.filter(category=category_filter)

    if event_type_filter:
        events = events.filter(event_type=event_type_filter)
        
    if date_filter:
        try:
            parsed_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            events = events.filter(date__date=parsed_date)
        except ValueError:
            pass
            
    events_qs = events.order_by('date')
    paginator = Paginator(events_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
            
    # Metrics analytics for hero banner & countdown
    all_approved = Event.objects.filter(is_approved=True)
    next_event = all_approved.filter(date__gte=timezone.now()).order_by('date').first()
    total_events = all_approved.count()
    total_attendees = Registration.objects.filter(event__is_approved=True).count()
    virtual_count = all_approved.filter(event_type='VIRTUAL').count()
    in_person_count = all_approved.filter(event_type='IN_PERSON').count()
    active_organizers = all_approved.values('organizer').distinct().count()
    
    locations = all_approved.values_list('location', flat=True).distinct()
    categories = Event.CATEGORY_CHOICES
    
    context = {
        'events': page_obj,
        'page_obj': page_obj,
        'query': query,
        'location_filter': location_filter,
        'date_filter': date_filter,
        'category_filter': category_filter,
        'event_type_filter': event_type_filter,
        'locations': locations,
        'categories': categories,
        'total_events': total_events,
        'total_attendees': total_attendees,
        'virtual_count': virtual_count,
        'in_person_count': in_person_count,
        'active_organizers': active_organizers,
        'next_event': next_event,
    }
    return render(request, 'events/event_list.html', context)

@login_required
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    
    if not event.is_approved and not request.user.is_staff and event.organizer != request.user:
        raise PermissionDenied("You do not have permission to view this pending event.")
        
    registration = Registration.objects.filter(user=request.user, event=event).first() if request.user.is_authenticated else None
    already_registered = registration is not None
    user_tickets = registration.quantity if registration else 0
    max_tickets_per_user = 5
    max_addable_user = max(0, max_tickets_per_user - user_tickets)
    slots_left = event.slots_left
    max_selectable = min(max_addable_user, slots_left)
    total_booked = event.total_booked_tickets
    
    attendees = []
    if request.user.is_staff or request.user == event.organizer:
        attendees = Registration.objects.filter(event=event).select_related('user').order_by('-registered_at')
    
    context = {
        'event': event,
        'registration': registration,
        'already_registered': already_registered,
        'user_tickets': user_tickets,
        'max_tickets_per_user': max_tickets_per_user,
        'max_addable_user': max_addable_user,
        'max_selectable': max_selectable,
        'registrations_count': total_booked,
        'slots_left': slots_left,
        'attendees': attendees,
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
        category = request.POST.get('category', 'OTHER').strip()
        event_type = request.POST.get('event_type', 'IN_PERSON').strip()
        speaker_name = request.POST.get('speaker_name', '').strip()
        speaker_role = request.POST.get('speaker_role', '').strip()

        context_data = {
            'categories': Event.CATEGORY_CHOICES,
            'event_types': Event.EVENT_TYPE_CHOICES,
            'title': title,
            'description': description,
            'location': location,
            'date_val': date_str,
            'capacity': capacity,
            'category_val': category,
            'event_type_val': event_type,
            'speaker_name': speaker_name,
            'speaker_role': speaker_role,
        }

        if not (title and description and location and date_str and capacity):
            messages.error(request, "All required fields must be filled out.")
            return render(request, 'events/create_event.html', context_data)

        try:
            capacity_val = int(capacity)
            if capacity_val <= 0:
                raise ValueError()
            if capacity_val > 100000:
                messages.error(request, "Capacity cannot exceed 100,000 attendees.")
                return render(request, 'events/create_event.html', context_data)
        except ValueError:
            messages.error(request, "Capacity must be a positive number.")
            return render(request, 'events/create_event.html', context_data)

        event_date = parse_event_date(date_str)
        if not event_date:
            messages.error(request, "Invalid date format.")
            return render(request, 'events/create_event.html', context_data)

        if event_date < (timezone.now() - timedelta(minutes=10)):
            messages.error(request, "Event date must be in the future.")
            return render(request, 'events/create_event.html', context_data)

        event = Event.objects.create(
            title=title,
            description=description,
            location=location,
            date=event_date,
            capacity=capacity_val,
            category=category,
            event_type=event_type,
            speaker_name=speaker_name,
            speaker_role=speaker_role,
            organizer=request.user,
            is_approved=False
        )
        # Handle optional banner image upload
        if 'image' in request.FILES:
            event.image = request.FILES['image']
            event.save()

        messages.success(request, f"Event '{title}' created successfully! It will be visible once approved by an administrator.")
        return redirect('event_list')

    return render(request, 'events/create_event.html', {'categories': Event.CATEGORY_CHOICES, 'event_types': Event.EVENT_TYPE_CHOICES})

@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    if event.organizer != request.user and not request.user.is_staff:
        raise PermissionDenied("You do not have permission to edit this event.")
        
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        location = request.POST.get('location', '').strip()
        date_str = request.POST.get('date', '').strip()
        capacity = request.POST.get('capacity', '').strip()
        category = request.POST.get('category', 'OTHER').strip()
        event_type = request.POST.get('event_type', 'IN_PERSON').strip()
        speaker_name = request.POST.get('speaker_name', '').strip()
        speaker_role = request.POST.get('speaker_role', '').strip()
        
        context_data = {
            'event': event,
            'categories': Event.CATEGORY_CHOICES,
            'event_types': Event.EVENT_TYPE_CHOICES,
            'formatted_date': date_str
        }

        if not (title and description and location and date_str and capacity):
            messages.error(request, "All required fields must be filled out.")
            return render(request, 'events/edit_event.html', context_data)
            
        try:
            capacity_val = int(capacity)
            if capacity_val <= 0:
                raise ValueError()
            if capacity_val > 100000:
                messages.error(request, "Capacity cannot exceed 100,000 attendees.")
                return render(request, 'events/edit_event.html', context_data)
        except ValueError:
            messages.error(request, "Capacity must be a positive number.")
            return render(request, 'events/edit_event.html', context_data)
            
        event_date = parse_event_date(date_str)
        if not event_date:
            messages.error(request, "Invalid date format.")
            return render(request, 'events/edit_event.html', context_data)
            
        if event_date < (timezone.now() - timedelta(minutes=10)):
            messages.error(request, "Event date must be in the future.")
            return render(request, 'events/edit_event.html', context_data)
            
        event.title = title
        event.description = description
        event.location = location
        event.date = event_date
        event.capacity = capacity_val
        event.category = category
        event.event_type = event_type
        event.speaker_name = speaker_name
        event.speaker_role = speaker_role
        # Handle optional banner image upload / replacement
        if 'image' in request.FILES:
            event.image = request.FILES['image']
        event.save()

        messages.success(request, f"Event '{title}' updated successfully.")
        return redirect('event_detail', pk=event.id)

    formatted_date = event.date.strftime('%Y-%m-%dT%H:%M') if event.date else ''
    return render(request, 'events/edit_event.html', {
        'event': event,
        'formatted_date': formatted_date,
        'categories': Event.CATEGORY_CHOICES,
        'event_types': Event.EVENT_TYPE_CHOICES
    })


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
    if not request.user.is_staff:
        raise PermissionDenied("Only administrators can approve events.")

    if request.method == 'POST':
        event = get_object_or_404(Event, id=event_id)
        event.is_approved = True
        event.save()
        messages.success(request, f"Event '{event.title}' has been successfully approved.")
        return redirect('/admin/')

    return redirect('/admin/')

@login_required
def reject_event_view(request, event_id):
    if not request.user.is_staff:
        raise PermissionDenied("Only administrators can reject events.")

    if request.method == 'POST':
        event = get_object_or_404(Event, id=event_id)
        title = event.title
        event.delete()
        messages.success(request, f"Event '{title}' has been rejected and deleted.")
        return redirect('/admin/')

    return redirect('/admin/')

@login_required
def register_for_event(request, event_id):
    user = request.user

    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)

    quantity_raw = request.POST.get('quantity', 1)
    try:
        quantity = int(quantity_raw)
        if quantity < 1:
            return JsonResponse({"error": "Ticket quantity must be at least 1."}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Quantity must be a valid positive integer."}, status=400)

    try:
        reg = register_user_for_event(user, event_id, quantity=quantity)
        is_new = getattr(reg, 'is_new', False)
        status_code = 201 if is_new else 200
        return JsonResponse({
            "message": f"Successfully reserved {quantity} ticket(s)! You now hold {reg.quantity} ticket(s) total.",
            "ticket_code": reg.ticket_code,
            "user_tickets": reg.quantity,
            "slots_left": reg.event.slots_left
        }, status=status_code)
    except RegistrationError as e:
        return JsonResponse({"error": e.message}, status=e.status_code)
    except Event.DoesNotExist:
        return JsonResponse({"error": "Event not found"}, status=404)

@login_required
def unregister_from_event(request, event_id):
    user = request.user
    
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
        
    try:
        with transaction.atomic():
            event = Event.objects.select_for_update().get(id=event_id)
            registration = Registration.objects.filter(user=user, event=event).first()
            if not registration:
                return JsonResponse({"error": "You are not registered for this event."}, status=400)
                
            registration.delete()
            return JsonResponse({"message": "Successfully cancelled registration!"}, status=200)
            
    except Event.DoesNotExist:
        return JsonResponse({"error": "Event not found"}, status=404)

@login_required
def user_dashboard(request):
    user = request.user
    my_registrations = Registration.objects.filter(user=user).select_related('event').order_by('event__date')
    my_events = Event.objects.filter(organizer=user).order_by('-created_at')
    
    context = {
        'my_registrations': my_registrations,
        'my_events': my_events,
    }
    return render(request, 'events/user_dashboard.html', context)

@login_required
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if event.organizer != request.user and not request.user.is_staff:
        raise PermissionDenied("You do not have permission to delete this event.")

    if request.method == 'POST':
        title = event.title
        event.delete()
        messages.success(request, f"Event '{title}' deleted successfully.")
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('user_dashboard')

    return redirect('event_detail', pk=event.id)


@login_required
def view_ticket(request, registration_id):
    """Render a QR-code ticket for the given registration.
    Only the ticket owner or staff may view it.
    """
    registration = get_object_or_404(Registration, id=registration_id)

    if registration.user != request.user and not request.user.is_staff:
        raise PermissionDenied("You are not allowed to view this ticket.")

    qr_b64 = None
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=8,
            border=3,
        )
        qr.add_data(registration.ticket_code)
        qr.make(fit=True)
        qr_img = qr.make_image(
            fill_color='#db2777',
            back_color='#060913',
            image_factory=PilImage
        )

        buffer = io.BytesIO()
        qr_img.save(buffer, format='PNG')
        qr_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        logger.info(f"Generated ticket QR code base64 length: {len(qr_b64)}")
        print(f"[TICKET QR] Generated base64 length: {len(qr_b64)}")
    except Exception as e:
        logger.error(f"Error generating QR code for ticket {registration.ticket_code}: {e}", exc_info=True)
        print(f"[TICKET QR ERROR] Failed to generate QR code: {e}")

    context = {
        'registration': registration,
        'event': registration.event,
        'qr_code_b64': qr_b64,
    }
    return render(request, 'events/ticket.html', context)
