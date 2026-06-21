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
            # Synchronize thread start using a barrier
            barrier.wait()
            
            try:
                response = client.post(reverse('register_for_event', args=[self.event.id]))
                results.append((user.username, response.status_code, response.content.decode()))
            except Exception as e:
                results.append((user.username, 999, str(e)))
        
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
        # The other threads should get rejected cleanly (or blocked/locked by SQLite)
        # In SQLite, some threads might get database locked errors, but under no circumstances should they register
        print(f"Concurrency simulation: 10 threads, {len(success_responses)} success, {len(error_responses)} rejected/locked.")
