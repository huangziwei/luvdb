from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase

from .models import CustomUser


class CustomUserModelTest(TestCase):
    def test_create_user_with_all_details(self):
        # Test creating a user with all fields properly set
        user = CustomUser.objects.create_user(
            username="newuser",
            email="newuser@example.com",
            password="testpass123",
            display_name="New User",
            bio="Just a new user.",
            is_public=True,
            pure_text_mode=False,
            timezone="UTC",
            enable_replies_by_default=True,
            enable_share_to_feed_by_default=False,
        )
        user.save()
        self.assertEqual(user.username, "newuser")
        self.assertFalse(user.is_deactivated)

    def test_create_user_with_minimal_details(self):
        # Test creating a user with only the required fields
        user = CustomUser.objects.create_user(
            username="minimaluser", password="testpass123"
        )
        user.save()
        self.assertEqual(user.username, "minimaluser")

    def test_invalid_username(self):
        # Test to ensure invalid usernames are caught
        with self.assertRaises(ValidationError):
            user = CustomUser.objects.create_user(
                username="admin",  # 'admin' is a reserved username
                password="testpass123",
            )
            user.clean()  # Explicitly call clean to trigger validation

    def test_missing_non_nullable_fields(self):
        # Test that missing non-nullable fields raise an IntegrityError
        with self.assertRaises(IntegrityError):
            user = CustomUser(username="testuser")  # Missing password
            user.save()

    def test_duplicate_username(self):
        # Ensure that creating a user with a duplicate username raises an IntegrityError
        user1 = CustomUser.objects.create_user(
            username="uniqueuser", password="testpass123"
        )
        user1.save()

        with self.assertRaises(IntegrityError):
            user2 = CustomUser.objects.create_user(
                username="uniqueuser", password="differentpass"
            )
            user2.save()
