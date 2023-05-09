from django.test import TestCase, Client
from .models import Account, UserProfile
from .forms import RegistrationForm, UserForm, UserProfileForm
from carts.models import Cart, CartItem
from django.contrib.auth import authenticate
from django.test import Client
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.core import mail
from django.contrib.auth import get_user_model
from django.urls import reverse

# Create your tests here.


class AccountModelTest(TestCase):

    def setUp(self):
        self.user = Account.objects.create_user(
            first_name='John',
            last_name='Doe',
            email='johndoe@example.com',
            username='johndoe',
            password='password'
        )

    def test_create_account(self):
        self.assertEqual(self.user.email, 'johndoe@example.com')
        self.assertEqual(self.user.username, 'johndoe')
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.last_name, 'Doe')
        self.assertEqual(self.user.full_name(), 'John Doe')

    def test_create_superuser(self):
        superuser = Account.objects.create_superuser(
            first_name='Admin',
            last_name='User',
            email='admin@example.com',
            username='admin',
            password='password'
        )
        self.assertTrue(superuser.is_admin)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_active)
        self.assertTrue(superuser.is_superadmin)


class UserProfileModelTest(TestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            first_name='John',
            last_name='Doe',
            email='johndoe@example.com',
            username='johndoe',
            password='password'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            address_line_1='123 Main St',
            city='Anytown',
            state='CA',
            country='USA'
        )

    def test_create_user_profile(self):
        self.assertEqual(self.profile.user.email, 'johndoe@example.com')
        self.assertEqual(self.profile.address_line_1, '123 Main St')
        self.assertEqual(self.profile.city, 'Anytown')
        self.assertEqual(self.profile.state, 'CA')
        self.assertEqual(self.profile.country, 'USA')
        self.assertEqual(self.profile.full_address(), '123 Main St ')


class TestForms(TestCase):
    def test_registration_form_valid_data(self):
        form = RegistrationForm(data={
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '1234567890',
            'email': 'johndoe@example.com',
            'password': 'test1234',
            'confirm_password': 'test1234',
        })

        self.assertTrue(form.is_valid())

    def test_registration_form_passwords_do_not_match(self):
        form = RegistrationForm(data={
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '1234567890',
            'email': 'johndoe@example.com',
            'password': 'test1234',
            'confirm_password': 'test12345',
        })

        self.assertFalse(form.is_valid())

    def test_user_form_valid_data(self):
        form = UserForm(data={
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '1234567890',
        })

        self.assertTrue(form.is_valid())

    def test_user_profile_form_valid_data(self):
        form = UserProfileForm(data={
            'address_line_1': '123 Main St',
            'address_line_2': '',
            'city': 'Anytown',
            'state': 'CA',
            'country': 'USA',
            'profile_picture': None,
        })

        self.assertTrue(form.is_valid())


class RegisterViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.user_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '1234567890',
            'email': 'johndoe@example.com',
            'password': 'test1234',
            'confirm_password': 'test1234',
        }

    def test_register_view_success_status_code(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)

    def test_register_view_form(self):
        response = self.client.get(self.register_url)
        form = response.context.get('form')
        self.assertIsInstance(form, RegistrationForm)

    def test_register_view_post_success(self):
        response = self.client.post(self.register_url, self.user_data)
        self.assertRedirects(response, self.register_url)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject,
                         'Please activate your account')
        self.assertEqual(mail.outbox[0].to[0], self.user_data['email'])

    def test_register_view_post_fail(self):
        self.user_data['confirm_password'] = 'test12345'
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Password does not match!')

    def test_register_view_user_created(self):
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(UserProfile.objects.count(), 1)

    def test_register_view_user_not_created(self):
        self.user_data['email'] = ''
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(get_user_model().objects.count(), 0)
        self.assertEqual(UserProfile.objects.count(), 0)


class LoginTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = Account.objects.create_user(
            email='test@example.com',
            password='testpassword',
            first_name='Test',
            last_name='User',
        )

    def test_login_verified_user_with_empty_cart(self):
        response = self.client.post(reverse('login'), {
            'email': 'test@example.com',
            'password': 'testpassword',
        })
        self.assertRedirects(response, '/')
        user = self.client.get(reverse('account')).context['user']
        self.assertEqual(user, self.user)

    def test_login_verified_user_with_non_empty_cart(self):
        cart = Cart.objects.create(cart_id='testcart')
        CartItem.objects.create(cart=cart, product_id=1, quantity=1)
        CartItem.objects.create(cart=cart, product_id=2, quantity=1)
        response = self.client.post(reverse('login'), {
            'email': 'test@example.com',
            'password': 'testpassword',
        })
        self.assertRedirects(response, '/')
        user = self.client.get(reverse('account')).context['user']
        self.assertEqual(user, self.user)
        # Verify that the user ID has been saved in each cart item
        cart_items = CartItem.objects.all()
        for item in cart_items:
            self.assertEqual(item.user_id, self.user.id)

    def test_login_unverified_user(self):
        User.objects.filter(pk=self.user.pk).update(email_verified=False)
        response = self.client.post(reverse('login'), {
            'email': 'test@example.com',
            'password': 'testpassword',
        })
        self.assertRedirects(response, reverse('login'))
        user = self.client.get(reverse('account')).context['user']
        self.assertIsNone(user)

    def test_login_with_invalid_credentials(self):
        response = self.client.post(reverse('login'), {
            'email': 'test@example.com',
            'password': 'invalidpassword',
        })
        self.assertRedirects(response, reverse('login'))
        user = self.client.get(reverse('account')).context['user']
        self.assertIsNone(user)


class LogoutViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('logout')
        self.user = Account.objects.create_user(
            username='testuser',
            email='testuser@test.com',
            password='testpass',
            first_name='user',
            last_name='test'
        )

    def test_logout_view(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('login'))
        user = authenticate(username='testuser', password='testpass')
        self.assertIsNone(user)

    def test_logout_message(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(self.url, follow=True)
        message = list(response.context.get('messages'))[0]
        self.assertEqual(str(message), 'You are logged out.')


class ActivateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = Account.objects.create_user(
            username='testuser',
            email='testuser@test.com',
            password='testpass',
            first_name='user',
            last_name='test'
        )
        self.url = reverse('activate', args=[urlsafe_base64_encode(
            force_bytes(self.user.pk)), default_token_generator.make_token(self.user)])

    def test_activation_success(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('login'))
        user = get_user_model().objects.get(pk=self.user.pk)
        self.assertTrue(user.is_active)
        message = list(response.context.get('messages'))[0]
        self.assertEqual(
            str(message), 'Congratulations! Your account is activated.')

    def test_activation_invalid_link(self):
        self.url = reverse('activate', args=[urlsafe_base64_encode(
            force_bytes(self.user.pk)), 'invalidtoken'])
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('register'))
        user = get_user_model().objects.get(pk=self.user.pk)
        self.assertFalse(user.is_active)
        message = list(response.context.get('messages'))[0]
        self.assertEqual(str(message), 'Invalid activation link')


class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.dashboard_url = reverse('dashboard')
        self.forgot_password_url = reverse('forgotPassword')
        self.reset_password_email_subject = 'Reset Your Password'

        # create a user for testing
        self.user = Account.objects.create_user(
            first_name='John',
            last_name='Doe',
            username='johndoe',
            email='johndoe@test.com',
            password='testpassword'
        )

        self.user_profile = UserProfile.objects.create(
            user=self.user,
            address_line_1='123 Main St',
            address_line_2='',
            city='Test City',
            state='Test State',
            country='US'
        )

    def test_dashboard_GET_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get(self.dashboard_url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/dashboard.html')

    def test_dashboard_GET_unauthenticated_user(self):
        response = self.client.get(self.dashboard_url)
        self.assertEquals(response.status_code, 302)
        self.assertRedirects(response, '/login/?next=/dashboard/')

    def test_forgot_password_GET(self):
        response = self.client.get(self.forgot_password_url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/forgotPassword.html')

    def test_forgot_password_POST_with_existing_account(self):
        response = self.client.post(
            self.forgot_password_url, {'email': 'johndoe@test.com'})

        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].subject,
                          self.reset_password_email_subject)

        messages = list(response.context['messages'])
        self.assertEquals(len(messages), 1)
        self.assertEquals(str(messages[0]),
                          'Password reset email has been sent to your email address.')
        self.assertRedirects(response, reverse('login'))

    def test_forgot_password_POST_with_non_existing_account(self):
        response = self.client.post(reverse('forgotPassword'), {
            'email': 'non_existing_email@example.com'
        })

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('forgotPassword'))
        if response.context:
            messages = list(response.context['messages'])
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), 'Account does not exist!')
