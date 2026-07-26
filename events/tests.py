from django.test import TransactionTestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Event, Registration
import threading
import time

class EventManagementRBACAndConcurrencyTests(TransactionTestCase):
    def setUp(self):
        # Create users
        self.staff_user = User.objects.create_user(username='admin_staff', password='adminpassword', is_staff=True)
        self.normal_user = User.objects.create_user(username='normal_user', password='userpassword')
        self.normal_user2 = User.objects.create_user(username='normal_user2', password='userpassword2')
        
        # Create a pending event organized by normal_user
        self.event = Event.objects.create(
            title="Advanced Backend Concurrency",
            description="Mastering database row locking and transaction boundaries.",
            location="Silicon Valley",
            date=timezone.now() + timezone.timedelta(days=7),
            capacity=1, # Very limited capacity to test overbooking
            organizer=self.normal_user,
            is_approved=False
        )

    def test_rbac_approval_denied_for_normal_user(self):
        # Log in normal user
        self.client.login(username='normal_user', password='userpassword')
        
        # Attempt to approve event (should fail with PermissionDenied/403)
        response = self.client.post(reverse('approve_event', args=[self.event.id]))
        self.assertEqual(response.status_code, 403)
        
        # Verify event is still not approved
        self.event.refresh_from_db()
        self.assertFalse(self.event.is_approved)

    def test_rbac_approval_granted_for_staff_user(self):
        # Log in staff user
        self.client.login(username='admin_staff', password='adminpassword')
        
        # Approve event
        response = self.client.post(reverse('approve_event', args=[self.event.id]))
        self.assertEqual(response.status_code, 302) # Redirect back to dashboard
        
        # Verify event is approved
        self.event.refresh_from_db()
        self.assertTrue(self.event.is_approved)

    def test_cannot_register_for_unapproved_event(self):
        self.client.login(username='normal_user2', password='userpassword2')
        response = self.client.post(reverse('register_for_event', args=[self.event.id]))
        self.assertEqual(response.status_code, 400)
        self.assertIn("unapproved", response.json()['error'])

    def test_concurrency_and_overbooking_prevention(self):
        # First, approve the event
        self.event.is_approved = True
        self.event.save()
        
        # Create multiple user accounts to register concurrently
        users = []
        for i in range(10):
            u = User.objects.create_user(username=f'candidate_{i}', password='password123')
            users.append(u)
            
        # Prepare authenticated clients sequentially to avoid SQLite locks during thread setup
        clients_and_users = []
        for user in users:
            client = Client()
            client.login(username=user.username, password='password123')
            clients_and_users.append((client, user))
            
        results = []
        threads = []
        barrier = threading.Barrier(len(users))
        
        def attempt_registration(client, user):
            barrier.wait()
            
            for _ in range(20):
                try:
                    response = client.post(reverse('register_for_event', args=[self.event.id]))
                    if response.status_code == 503:
                        time.sleep(0.08)
                        continue
                    results.append((user.username, response.status_code, response.content.decode()))
                    break
                except Exception as e:
                    time.sleep(0.08)
            else:
                results.append((user.username, 999, "Max retries reached due to DB lock"))
        
        # Spawn threads
        for client, user in clients_and_users:
            t = threading.Thread(target=attempt_registration, args=(client, user))
            threads.append(t)
            t.start()
            
        # Wait for all threads to finish
        for t in threads:
            t.join()
            
        # Verify that only exactly 1 registration was successfully created in the database
        registration_count = Registration.objects.filter(event=self.event).count()
        self.assertEqual(registration_count, 1, "Concurrency issue: Event was overbooked!")
        
        # Count successful responses vs failures
        success_responses = [r for r in results if r[1] == 201]
        error_responses = [r for r in results if r[1] == 400]
        
        self.assertEqual(len(success_responses), 1, "Exactly one thread should receive a 201 Created success response.")
        print(f"Concurrency simulation: 10 threads, {len(success_responses)} success, {len(error_responses)} rejected/locked.")

    def test_unregister_from_event(self):
        self.event.is_approved = True
        self.event.save()
        
        # Register user
        self.client.login(username='normal_user2', password='userpassword2')
        reg_response = self.client.post(reverse('register_for_event', args=[self.event.id]))
        self.assertEqual(reg_response.status_code, 201)
        self.assertTrue(Registration.objects.filter(user=self.normal_user2, event=self.event).exists())
        
        # Unregister user
        unreg_response = self.client.post(reverse('unregister_from_event', args=[self.event.id]))
        self.assertEqual(unreg_response.status_code, 200)
        self.assertFalse(Registration.objects.filter(user=self.normal_user2, event=self.event).exists())

    def test_cannot_create_event_with_past_date(self):
        self.client.login(username='normal_user', password='userpassword')
        past_date_str = (timezone.now() - timezone.timedelta(days=2)).strftime('%Y-%m-%dT%H:%M')
        
        response = self.client.post(reverse('create_event'), {
            'title': 'Past Hackathon',
            'description': 'Event in the past',
            'location': 'Online',
            'capacity': '10',
            'date': past_date_str
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Event.objects.filter(title='Past Hackathon').exists())

    def test_admin_reject_event(self):
        self.client.login(username='admin_staff', password='adminpassword')
        response = self.client.post(reverse('reject_event', args=[self.event.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Event.objects.filter(id=self.event.id).exists())

    def test_user_dashboard(self):
        self.client.login(username='normal_user', password='userpassword')
        response = self.client.get(reverse('user_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.event.title)

    def test_edit_and_delete_event(self):
        self.client.login(username='normal_user', password='userpassword')
        future_date_str = (timezone.now() + timezone.timedelta(days=10)).strftime('%Y-%m-%dT%H:%M')
        
        # Edit event
        edit_resp = self.client.post(reverse('edit_event', args=[self.event.id]), {
            'title': 'Updated Concurrency Title',
            'description': 'Updated description',
            'location': 'San Francisco',
            'capacity': '50',
            'date': future_date_str
        })
        self.assertEqual(edit_resp.status_code, 302)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, 'Updated Concurrency Title')
        
        # Delete event
        del_resp = self.client.post(reverse('delete_event', args=[self.event.id]))
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(Event.objects.filter(id=self.event.id).exists())

    def test_ticket_code_generation(self):
        self.event.is_approved = True
        self.event.save()
        
        reg = Registration.objects.create(user=self.normal_user2, event=self.event)
        self.assertTrue(reg.ticket_code.startswith("TIC-"))
        self.assertEqual(len(reg.ticket_code), 12)

    def test_category_and_event_type_filtering(self):
        e1 = Event.objects.create(
            title="Python Tech Summit",
            description="Deep dive into Python GIL and AsyncIO",
            location="Virtual",
            date=timezone.now() + timezone.timedelta(days=3),
            capacity=100,
            category="CONFERENCE",
            event_type="VIRTUAL",
            speaker_name="Guido van Rossum",
            speaker_role="Python Creator",
            organizer=self.staff_user,
            is_approved=True
        )
        
        response = self.client.get(reverse('event_list') + '?category=CONFERENCE')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Tech Summit")
        self.assertContains(response, "Guido van Rossum")

    def test_django_admin_access_and_models(self):
        self.staff_user.is_superuser = True
        self.staff_user.save()
        self.client.login(username='admin_staff', password='adminpassword')
        response = self.client.get(reverse('admin:events_event_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Wiwi Events Admin")

    def test_password_validation_on_registration(self):
        # Attempt registering with weak password (e.g. '123')
        response = self.client.post(reverse('register'), {
            'username': 'new_weak_user',
            'email': 'weak@example.com',
            'password': '123',
            'confirm_password': '123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='new_weak_user').exists())

    def test_capacity_upper_bound_limit(self):
        self.client.login(username='normal_user', password='userpassword')
        future_date_str = (timezone.now() + timezone.timedelta(days=15)).strftime('%Y-%m-%dT%H:%M')
        
        response = self.client.post(reverse('create_event'), {
            'title': 'Mega Stadium Concert',
            'description': 'Over capacity test',
            'location': 'Wembley',
            'capacity': '9999999', # Exceeds 100,000 limit
            'date': future_date_str
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot exceed 100,000")
        self.assertFalse(Event.objects.filter(title='Mega Stadium Concert').exists())

    def test_event_list_pagination(self):
        # Create 15 approved events
        for i in range(15):
            Event.objects.create(
                title=f"Paginated Event {i}",
                description="Testing pagination",
                location="Online",
                date=timezone.now() + timezone.timedelta(days=i+1),
                capacity=100,
                organizer=self.staff_user,
                is_approved=True
            )

        resp_page1 = self.client.get(reverse('event_list'))
        self.assertEqual(resp_page1.status_code, 200)
        self.assertEqual(len(resp_page1.context['events']), 12) # 12 items on page 1

        resp_page2 = self.client.get(reverse('event_list') + '?page=2')
        self.assertEqual(resp_page2.status_code, 200)
        self.assertEqual(len(resp_page2.context['events']), 3) # 3 items on page 2


from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token


class DRFAPITests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username='staff_api', password='password123', is_staff=True)
        self.user1 = User.objects.create_user(username='user1_api', password='password123')
        self.user2 = User.objects.create_user(username='user2_api', password='password123')

        self.approved_event = Event.objects.create(
            title="API Tech Summit",
            description="REST API Best Practices",
            location="Virtual Zoom",
            date=timezone.now() + timezone.timedelta(days=5),
            capacity=1,
            category="CONFERENCE",
            event_type="VIRTUAL",
            organizer=self.staff_user,
            is_approved=True
        )

        self.unapproved_event = Event.objects.create(
            title="Draft API Workshop",
            description="Work in progress",
            location="Room B",
            date=timezone.now() + timezone.timedelta(days=10),
            capacity=10,
            organizer=self.user1,
            is_approved=False
        )

    def test_obtain_auth_token(self):
        response = self.client.post(reverse('api_token_auth'), {
            'username': 'user1_api',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.json())

    def test_event_list_visibility(self):
        # Anonymous user sees only approved events
        response = self.client.get(reverse('event-list'))
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.approved_event.id)

        # Authenticated user1 sees approved events + own unapproved event
        token, _ = Token.objects.get_or_create(user=self.user1)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        response = self.client.get(reverse('event-list'))
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(len(results), 2)

    def test_create_event_api(self):
        token, _ = Token.objects.get_or_create(user=self.user1)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        data = {
            'title': 'New API Event',
            'description': 'Created via REST API',
            'location': 'Online Hub',
            'date': (timezone.now() + timezone.timedelta(days=15)).isoformat(),
            'capacity': 30,
            'category': 'WORKSHOP',
            'event_type': 'IN_PERSON'
        }
        response = self.client.post(reverse('event-list'), data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.json()['slots_left'] < 30)

        # Verify event created in DB with is_approved=False and organizer=user1
        event = Event.objects.get(id=response.json()['id'])
        self.assertEqual(event.organizer, self.user1)
        self.assertFalse(event.is_approved)

    def test_api_registration_flow_and_capacity(self):
        token1, _ = Token.objects.get_or_create(user=self.user1)
        token2, _ = Token.objects.get_or_create(user=self.user2)

        # User1 registers for capacity-1 approved event
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token1.key)
        reg_resp = self.client.post(reverse('registration-list'), {'event': self.approved_event.id}, format='json')
        self.assertEqual(reg_resp.status_code, 201)
        self.assertIn('ticket_code', reg_resp.json())

        # User1 attempts to register again -> 400 Bad Request
        reg_dup_resp = self.client.post(reverse('registration-list'), {'event': self.approved_event.id}, format='json')
        self.assertEqual(reg_dup_resp.status_code, 400)
        self.assertIn('already registered', reg_dup_resp.json()['detail'].lower())

        # User2 attempts to register for full event -> 400 Bad Request (overbooking prevented)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token2.key)
        full_resp = self.client.post(reverse('registration-list'), {'event': self.approved_event.id}, format='json')
        self.assertEqual(full_resp.status_code, 400)
        self.assertIn('fully booked', full_resp.json()['detail'].lower())





