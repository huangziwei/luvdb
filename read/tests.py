# Create your tests here.
from django.test import TestCase

from .models import Book, BookRole, Person, Publisher, Role, Work, WorkRole


##################
# Test models.py #
##################
class PersonModelTest(TestCase):
    def test_create_and_str(self):
        creator = Person.objects.create(name="Test Person")
        self.assertEqual(str(creator), "Test Person")


class PublisherModelTest(TestCase):
    def test_create_and_str(self):
        publisher_with_location = Publisher.objects.create(
            name="Test Publisher", location="Test Location"
        )
        self.assertEqual(str(publisher_with_location), "Test Location: Test Publisher")

        publisher_without_location = Publisher.objects.create(name="Test Publisher")
        self.assertEqual(str(publisher_without_location), "Test Publisher")


class RoleModelTest(TestCase):
    def test_create_and_str(self):
        role = Role.objects.create(name="Test Role")
        self.assertEqual(str(role), "Test Role")


class BookModelTest(TestCase):
    def test_create_and_str(self):
        book = Book.objects.create(title="Test Book")
        self.assertEqual(str(book), "Test Book")


class BookRoleModelTest(TestCase):
    def test_create_and_str(self):
        creator = Person.objects.create(name="Test Person")
        role = Role.objects.create(name="Test Role")
        book = Book.objects.create(title="Test Book")
        book_role = BookRole.objects.create(book=book, creator=creator, role=role)
        self.assertEqual(str(book_role), "Test Book - Test Person - Test Role")


class WorkModelTest(TestCase):
    def test_create_and_str(self):
        edition = Work.objects.create(edition_title="Test Work")
        self.assertEqual(str(edition), "Test Work")


class WorkRoleModelTest(TestCase):
    def test_create_and_str(self):
        creator = Person.objects.create(name="Test Person")
        role = Role.objects.create(name="Test Role")
        edition = Work.objects.create(edition_title="Test Work")
        edition_role = WorkRole.objects.create(
            edition=edition, creator=creator, role=role
        )
        self.assertEqual(str(edition_role), "Test Edition - Test Person - Test Role")
