from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import timedelta

from .models import TempCode, SweetblogProfile
from .forms import EmailForm, CodeForm, ProfileForm
from .views import get_device_id

User = get_user_model()


class AuthenticationModelTests(TestCase):
    """Test authentication models."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_temp_code_generation(self):
        """Test temporary code generation."""
        code = TempCode.generate_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
    
    def test_temp_code_validity(self):
        """Test temporary code validity check."""
        temp_code = TempCode.objects.create(
            email='test@example.com',
            code='123456'
        )
        
        # Fresh code should be valid
        self.assertTrue(temp_code.is_valid())
        
        # Used code should be invalid
        temp_code.is_used = True
        temp_code.save()
        self.assertFalse(temp_code.is_valid())
        
        # Expired code should be invalid
        temp_code.is_used = False
        temp_code.created_at = timezone.now() - timedelta(minutes=11)
        temp_code.save()
        self.assertFalse(temp_code.is_valid())
    
    def test_temp_code_cleanup(self):
        """Test expired code cleanup."""
        # Create fresh code
        fresh_code = TempCode.objects.create(
            email='fresh@example.com',
            code='111111'
        )
        
        # Create expired code
        expired_code = TempCode.objects.create(
            email='expired@example.com',
            code='222222'
        )
        expired_code.created_at = timezone.now() - timedelta(minutes=11)
        expired_code.save()
        
        # Run cleanup
        TempCode.cleanup_expired()
        
        # Fresh code should exist
        self.assertTrue(TempCode.objects.filter(id=fresh_code.id).exists())
        
        # Expired code should be deleted
        self.assertFalse(TempCode.objects.filter(id=expired_code.id).exists())
    
    def test_sweetblog_profile_creation(self):
        """Test SweetblogProfile creation."""
        profile = SweetblogProfile.objects.create(
            user=self.user,
            receive_newsletter=True
        )
        
        self.assertEqual(profile.user, self.user)
        self.assertTrue(profile.receive_newsletter)
        self.assertEqual(profile.linked_devices, [])
    
    def test_device_linking(self):
        """Test device linking functionality."""
        profile = SweetblogProfile.objects.create(user=self.user)
        device_id = 'test_device_123'
        
        # Device should not be linked initially
        self.assertFalse(profile.is_device_linked(device_id))
        
        # Link device
        profile.link_device(device_id)
        self.assertTrue(profile.is_device_linked(device_id))
        
        # Linking same device again should not duplicate
        profile.link_device(device_id)
        self.assertEqual(profile.linked_devices.count(device_id), 1)


class AuthenticationFormTests(TestCase):
    """Test authentication forms."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.profile = SweetblogProfile.objects.create(user=self.user)
    
    def test_email_form_valid(self):
        """Test valid email form."""
        form = EmailForm(data={'email': 'test@example.com'})
        self.assertTrue(form.is_valid())
    
    def test_email_form_invalid(self):
        """Test invalid email form."""
        form = EmailForm(data={'email': 'invalid-email'})
        self.assertFalse(form.is_valid())
    
    def test_code_form_valid(self):
        """Test valid code form."""
        form = CodeForm(data={
            'email': 'test@example.com',
            'code': '123456'
        })
        self.assertTrue(form.is_valid())
    
    def test_code_form_invalid(self):
        """Test invalid code form."""
        # Code too short
        form = CodeForm(data={
            'email': 'test@example.com',
            'code': '123'
        })
        self.assertFalse(form.is_valid())
    
    def test_profile_form(self):
        """Test profile form."""
        form = ProfileForm(
            data={
                'username': 'newusername',
                'receive_newsletter': True
            },
            instance=self.profile,
            user=self.user
        )
        
        self.assertTrue(form.is_valid())
        
        # Save form
        profile = form.save()
        
        # Check username was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'newusername')
        self.assertTrue(profile.receive_newsletter)


class AuthenticationViewTests(TestCase):
    """Test authentication views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='existinguser',
            email='existing@example.com'
        )
        self.profile = SweetblogProfile.objects.create(user=self.user)
    
    def test_get_device_id(self):
        """Test device ID generation."""
        request = MagicMock()
        request.META = {
            'HTTP_USER_AGENT': 'Test Browser',
            'REMOTE_ADDR': '127.0.0.1'
        }
        
        device_id = get_device_id(request)
        self.assertEqual(len(device_id), 32)
        
        # Same request should generate same ID
        device_id2 = get_device_id(request)
        self.assertEqual(device_id, device_id2)
    
    def test_connection_view_get(self):
        """Test GET request to connection view."""
        response = self.client.get(reverse('sweetblog_connection'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sweetblog/pico/auth/connection.html')
    
    def test_connection_view_new_user(self):
        """Test connection view with new user email."""
        email = 'newuser@example.com'
        
        response = self.client.post(
            reverse('sweetblog_connection'),
            data={'email': email}
        )
        
        # Should redirect to code view
        self.assertEqual(response.status_code, 302)
        self.assertIn('sweetblog_code', response.url)
        
        # User should be created
        self.assertTrue(User.objects.filter(email=email).exists())
        
        # Code should be created
        self.assertTrue(TempCode.objects.filter(email=email).exists())
        
        # Email should be sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [email])
    
    def test_connection_view_existing_user_new_device(self):
        """Test connection view with existing user on new device."""
        response = self.client.post(
            reverse('sweetblog_connection'),
            data={'email': 'existing@example.com'}
        )
        
        # Should redirect to code view
        self.assertEqual(response.status_code, 302)
        self.assertIn('sweetblog_code', response.url)
        
        # Code should be created
        self.assertTrue(TempCode.objects.filter(email='existing@example.com').exists())
        
        # Email should be sent
        self.assertEqual(len(mail.outbox), 1)
    
    def test_connection_view_existing_user_linked_device(self):
        """Test connection view with existing user on linked device."""
        # Link device first
        device_id = get_device_id(self.client.request)
        self.profile.link_device(device_id)
        
        response = self.client.post(
            reverse('sweetblog_connection'),
            data={'email': 'existing@example.com'}
        )
        
        # Should redirect to next URL (login successful)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        
        # User should be logged in
        self.assertIn('_auth_user_id', self.client.session)
    
    def test_code_view_get(self):
        """Test GET request to code view."""
        response = self.client.get(
            reverse('sweetblog_code'),
            {'email': 'test@example.com'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sweetblog/pico/auth/code.html')
    
    def test_code_view_valid_code(self):
        """Test code view with valid code."""
        email = 'existing@example.com'
        code = '123456'
        device_id = get_device_id(self.client.request)
        
        # Create valid code
        TempCode.objects.create(
            email=email,
            code=code,
            device_id=device_id
        )
        
        response = self.client.post(
            reverse('sweetblog_code'),
            data={'email': email, 'code': code}
        )
        
        # Should redirect to next URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        
        # User should be logged in
        self.assertIn('_auth_user_id', self.client.session)
        
        # Device should be linked
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.is_device_linked(device_id))
        
        # Code should be marked as used
        temp_code = TempCode.objects.get(email=email, code=code)
        self.assertTrue(temp_code.is_used)
    
    def test_code_view_invalid_code(self):
        """Test code view with invalid code."""
        response = self.client.post(
            reverse('sweetblog_code'),
            data={'email': 'test@example.com', 'code': '999999'}
        )
        
        # Should stay on same page with error
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'code', 'Invalid or expired code.')
    
    def test_profile_view_requires_login(self):
        """Test profile view requires authentication."""
        response = self.client.get(reverse('sweetblog_profile'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_profile_view_authenticated(self):
        """Test profile view for authenticated user."""
        self.client.force_login(self.user)
        
        response = self.client.get(reverse('sweetblog_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sweetblog/pico/auth/profile.html')
    
    def test_profile_view_update(self):
        """Test profile update."""
        self.client.force_login(self.user)
        
        response = self.client.post(
            reverse('sweetblog_profile'),
            data={
                'username': 'updatedusername',
                'receive_newsletter': True
            }
        )
        
        # Should redirect to next URL
        self.assertEqual(response.status_code, 302)
        
        # Username should be updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'updatedusername')
        
        # Profile should be updated
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.receive_newsletter)
    
    def test_next_parameter_propagation(self):
        """Test that next parameter is properly propagated."""
        next_url = '/some/page/'
        
        # Connection view
        response = self.client.get(
            reverse('sweetblog_connection') + f'?next={next_url}'
        )
        self.assertContains(response, f'next={next_url}')
        
        # Code view
        response = self.client.get(
            reverse('sweetblog_code') + f'?next={next_url}'
        )
        self.assertContains(response, f'next={next_url}')
        
        # Profile view
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('sweetblog_profile') + f'?next={next_url}'
        )
        self.assertContains(response, f'next={next_url}')


class AuthenticationIntegrationTests(TestCase):
    """Integration tests for full authentication flow."""
    
    def setUp(self):
        self.client = Client()
    
    def test_full_authentication_flow_new_user(self):
        """Test complete authentication flow for new user."""
        email = 'newuser@example.com'
        
        # Step 1: Submit email
        response = self.client.post(
            reverse('sweetblog_connection'),
            data={'email': email},
            follow=True
        )
        
        # Should be on code page
        self.assertTemplateUsed(response, 'sweetblog/pico/auth/code.html')
        
        # Get the code from email
        self.assertEqual(len(mail.outbox), 1)
        temp_code = TempCode.objects.get(email=email)
        
        # Step 2: Submit code
        response = self.client.post(
            reverse('sweetblog_code'),
            data={'email': email, 'code': temp_code.code},
            follow=True
        )
        
        # Should be logged in and redirected
        self.assertIn('_auth_user_id', self.client.session)
        
        # User should exist with profile
        user = User.objects.get(email=email)
        self.assertTrue(hasattr(user, 'sweetblog_profile'))
        
        # Device should be linked
        device_id = get_device_id(self.client.request)
        self.assertTrue(user.sweetblog_profile.is_device_linked(device_id))
        
        # Step 3: Update profile
        response = self.client.post(
            reverse('sweetblog_profile'),
            data={
                'username': 'mycustomusername',
                'receive_newsletter': True
            },
            follow=True
        )
        
        # Profile should be updated
        user.refresh_from_db()
        self.assertEqual(user.username, 'mycustomusername')
        self.assertTrue(user.sweetblog_profile.receive_newsletter)
    
    def test_return_visit_on_linked_device(self):
        """Test return visit on already linked device."""
        # Create user with linked device
        user = User.objects.create_user(
            username='returnuser',
            email='return@example.com'
        )
        profile = SweetblogProfile.objects.create(user=user)
        device_id = get_device_id(self.client.request)
        profile.link_device(device_id)
        
        # Try to login
        response = self.client.post(
            reverse('sweetblog_connection'),
            data={'email': 'return@example.com'},
            follow=True
        )
        
        # Should be logged in immediately
        self.assertIn('_auth_user_id', self.client.session)
        
        # No email should be sent
        self.assertEqual(len(mail.outbox), 0)