from django.urls import path

from .views import (
    BookAutocomplete,
    BookCreateView,
    BookDetailView,
    EditionCreateView,
    EditionDetailView,
    EditionUpdateView,
    PersonAutoComplete,
    PersonCreateView,
    PersonDetailView,
    PublisherAutocomplete,
    PublisherCreateView,
    PublisherDetailView,
    RoleAutocomplete,
)

app_name = "read"
urlpatterns = [
    # book
    path("book/new/", BookCreateView.as_view(), name="book_new"),
    path("book/<int:pk>/", BookDetailView.as_view(), name="book_detail"),
    # edition
    path("edition/new/", EditionCreateView.as_view(), name="edition_new"),
    path("edition/<int:pk>/", EditionDetailView.as_view(), name="edition_detail"),
    path("edition/<int:pk>/edit/", EditionUpdateView.as_view(), name="edition_edit"),
    # person
    path("person/new/", PersonCreateView.as_view(), name="person_create"),
    path("person/<int:pk>/", PersonDetailView.as_view(), name="person_detail"),
    # publisher
    path("publisher/new/", PublisherCreateView.as_view(), name="publisher_create"),
    path("publisher/<int:pk>/", PublisherDetailView.as_view(), name="publisher_detail"),
    # autocomplete views
    path("book-autocomplete/", BookAutocomplete.as_view(), name="book-autocomplete"),
    path(
        "publisher-autocomplete/",
        PublisherAutocomplete.as_view(),
        name="publisher-autocomplete",
    ),
    path(
        "person-autocomplete/", PersonAutoComplete.as_view(), name="person-autocomplete"
    ),
    path("role-autocomplete/", RoleAutocomplete.as_view(), name="role-autocomplete"),
]
