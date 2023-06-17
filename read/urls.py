from django.urls import path

from .views import (
    BookAutocomplete,
    BookCreateView,
    BookDetailView,
    BookUpdateView,
    EditionCreateView,
    EditionDetailView,
    EditionUpdateView,
    PersonAutoComplete,
    PersonCreateView,
    PersonDetailView,
    PersonUpdateView,
    PublisherAutocomplete,
    PublisherCreateView,
    PublisherDetailView,
    RoleAutocomplete,
    RoleCreateView,
)

app_name = "read"
urlpatterns = [
    # book
    path("book/create/", BookCreateView.as_view(), name="book_create"),
    path("book/<int:pk>/", BookDetailView.as_view(), name="book_detail"),
    path("book/<int:pk>/update/", BookUpdateView.as_view(), name="book_update"),
    # edition
    path("edition/create/", EditionCreateView.as_view(), name="edition_create"),
    path("edition/<int:pk>/", EditionDetailView.as_view(), name="edition_detail"),
    path(
        "edition/<int:pk>/update/", EditionUpdateView.as_view(), name="edition_update"
    ),
    # person
    path("person/create/", PersonCreateView.as_view(), name="person_create"),
    path("person/<int:pk>/", PersonDetailView.as_view(), name="person_detail"),
    path("person/<int:pk>/update/", PersonUpdateView.as_view(), name="person_update"),
    # role
    path("role/create/", RoleCreateView.as_view(), name="role_create"),
    # publisher
    path("publisher/create/", PublisherCreateView.as_view(), name="publisher_create"),
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
