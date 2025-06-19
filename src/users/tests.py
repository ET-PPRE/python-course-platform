import re

from allauth.account.models import EmailAddress, EmailConfirmation
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

# class SignupViewTests(TestCase):
#     def test_get_signup_page(self):
#         url = reverse('account_signup')
#         resp = self.client.get(url)
#         self.assertEqual(resp.status_code, 200)
#         self.assertTemplateUsed(resp, 'account/signup.html')

#     def test_creates_user_and_sends_email(self):
#         url = reverse('account_signup')
#         data = {
#             'email': 'test@uol.de',
#             'password1': 'P@ssword123!',
#             'password2': 'P@ssword123!',
#         }
#         resp = self.client.post(url, data)

#         # should redirect to the "verification sent" page
#         expected = reverse('account_email_verification_sent')
#         self.assertRedirects(resp, expected)

#         # one email should have been sent
#         self.assertEqual(len(mail.outbox), 1)


#         # django-allauth has behavior that a newly signed-up user has is_active=True
#         # even before they’ve clicked a verification link. Allauth doesn’t use the is_active flag to gate login.
#         # Allauth uses its own email‐verified flag on an EmailAddress record to decide 
#         # whether to let a user log in when ACCOUNT_EMAIL_VERIFICATION = "mandatory".

#         # users are active upon signup which is default behaviour of all-auth. 
#         # But they cannot login until mail verification. So, verify that users are active.

#         user = get_user_model().objects.get(email='test@uol.de')
#         email_address = EmailAddress.objects.get(user=user, email=user.email)
#         self.assertTrue(user.is_active) 

#         body = mail.outbox[0].body

#         # Extract the key via regex (allowing letters, numbers, hyphens, underscores)
#         match = re.search(r'confirm-email/([^/]+)/', body)
#         self.assertIsNotNone(match, "Confirmation link not found in e-mail body")
#         key = match.group(1)

#         # Build the confirmation URL and issue the GET
#         confirm_url = reverse('account_confirm_email', args=[key])
#         response = self.client.get(confirm_url)

#         self.assertEqual(response.status_code, 200)

#         # Assert the template used
#         self.assertTemplateUsed(response, "account/email_confirm.html")

#         # Before hitting the URL, the EmailAddress record should not be marked as verified
#         self.assertFalse(email_address.verified)

#         # Simulates clicking the <button type="submit">Confirm</button> in that form.
#         post_response = self.client.post(confirm_url)

#         # Because ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True and LOGIN_REDIRECT_URL = "home"
#         # allauth should now redirect straight to your `home` URL:
#         self.assertRedirects(post_response, reverse('home'))

#         # After hitting the URL, the EmailAddress record should be marked verified
#         email_address.refresh_from_db()
#         self.assertTrue(email_address.verified)

class LoginViewTests(TestCase):
    def setUp(self):
        # Create a user and mark their email as verified
        User = get_user_model()
        self.email = "loginuser@uol.de"
        self.password = "LoginPass!123"
        self.user = User.objects.create_user(email=self.email, password=self.password)
        # Create and verify EmailAddress so they can actually log in
        EmailAddress.objects.create(
            user=self.user, email=self.email, primary=True, verified=True
        )

    def test_login_page_renders_and_allows_authentication(self):
        # GET the login page
        login_url = reverse('account_login') + '?next=' + reverse('home')
        get_resp = self.client.get(login_url)
        self.assertEqual(get_resp.status_code, 200)
        self.assertTemplateUsed(get_resp, 'account/login.html')

        # POST valid credentials
        post_resp = self.client.post(login_url, {
            'login': self.email,
            'password': self.password,
        })

        # Should redirect to HOME
        self.assertRedirects(post_resp, reverse('home'))
        
        # Session now has authenticated user
        self.assertIn('_auth_user_id', self.client.session)

        # ensure that accessing home actually returns 200
        home_resp = self.client.get(reverse('home'))
        self.assertEqual(home_resp.status_code, 200)

    def test_login_with_invalid_credentials_shows_error(self):
        login_url = reverse('account_login')
        resp = self.client.post(login_url, {
            'login': self.email,
            'password': 'WrongPassword!',
        })
        # Invalid login re-renders the form
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'account/login.html')
        self.assertContains(
            resp,
            "The email address and/or password you specified are not correct.",
            html=False
        )