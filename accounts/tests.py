from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.forms import CustomUserCreationForm
from accounts.models import CustomUser, Follow, InvitationCode


class CustomUserCreationFormTest(TestCase):
    def setUp(self):
        # Create an inviter user
        self.inviter = CustomUser.objects.create_user(
            username="inviteruser", email="inviter@example.com", password="testpass123"
        )
        self.invitation_code = InvitationCode.objects.create(
            code="VALIDCODE", is_used=False, generated_by=self.inviter
        )

    def test_form_with_valid_data(self):
        form_data = {
            "username": "newuser",
            "invitation_code": "VALIDCODE",
            "signup_method": "password",
            "password1": "testpassword123",
            "password2": "testpassword123",
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.username, "newuser")
        self.assertTrue(user.check_password("testpassword123"))
        self.assertEqual(user.invited_by, self.inviter)
        # Verify that the follow relationships are created
        self.assertEqual(
            Follow.objects.filter(follower=user, followed=self.inviter).count(), 1
        )
        self.assertEqual(
            Follow.objects.filter(follower=self.inviter, followed=user).count(), 1
        )

    def test_passkey_signup_generates_password(self):
        form_data = {
            "username": "newuser",
            "invitation_code": "VALIDCODE",
            "signup_method": "passkey",
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertNotEqual(user.password, "")  # Check password is not empty
        self.assertEqual(user.invited_by, self.inviter)
        # Ensure that Follow objects are correctly created
        self.assertEqual(
            Follow.objects.filter(follower=user, followed=self.inviter).count(), 1
        )
        self.assertEqual(
            Follow.objects.filter(follower=self.inviter, followed=user).count(), 1
        )


class CustomUserModelTests(TestCase):
    def setUp(self):
        self.inviter = CustomUser.objects.create_user(
            username="inviter", password="test12345"
        )
        self.invitation_code = InvitationCode.objects.create(
            code="VALIDCODE", is_used=False, generated_by=self.inviter
        )

    def test_save_with_invited_by(self):
        # Test saving a user with an inviter
        user = CustomUser(
            username="testuser", password="password123", invited_by=self.inviter
        )
        user.save()
        self.assertEqual(user.invited_by, self.inviter)

    def test_user_with_reserved_username(self):
        # Test that creating a user with a reserved username fails
        with self.assertRaises(ValidationError):
            user = CustomUser(
                username="admin",  # 'admin' is a reserved username
                password="password123",
            )
            user.clean()  # Explicitly call clean to trigger validation

    def test_user_creation_follow_relations(self):
        user = CustomUser(
            username="follower",
            password="password123",
            code_used=self.invitation_code,
            invited_by=self.inviter,
        )
        user.save()

        self.assertIsNotNone(user.invited_by, "Invited by should not be None")
        follower_exists = Follow.objects.filter(
            follower=user, followed=self.inviter
        ).exists()
        followed_exists = Follow.objects.filter(
            follower=self.inviter, followed=user
        ).exists()
        self.assertTrue(follower_exists, "Follower relationship should exist")
        self.assertTrue(followed_exists, "Followed relationship should exist")
