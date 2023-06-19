# Create your tests here.
from django.test import TestCase

from .models import Book, BookRole, Edition, EditionRole, Person, Publisher, Role


##################
# Test models.py #
##################
class PersonModelTest(TestCase):
    def test_create_and_str(self):
        person = Person.objects.create(name="Test Person")
        self.assertEqual(str(person), "Test Person")


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
        person = Person.objects.create(name="Test Person")
        role = Role.objects.create(name="Test Role")
        book = Book.objects.create(title="Test Book")
        book_role = BookRole.objects.create(book=book, person=person, role=role)
        self.assertEqual(str(book_role), "Test Book - Test Person - Test Role")


class EditionModelTest(TestCase):
    def test_create_and_str(self):
        edition = Edition.objects.create(edition_title="Test Edition")
        self.assertEqual(str(edition), "Test Edition")


class EditionRoleModelTest(TestCase):
    def test_create_and_str(self):
        person = Person.objects.create(name="Test Person")
        role = Role.objects.create(name="Test Role")
        edition = Edition.objects.create(edition_title="Test Edition")
        edition_role = EditionRole.objects.create(
            edition=edition, person=person, role=role
        )
        self.assertEqual(str(edition_role), "Test Edition - Test Person - Test Role")