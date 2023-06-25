from django.urls import path

from .views import (
    BookCheckInAllListView,
    BookCheckInCreateView,
    BookCheckInDeleteView,
    BookCheckInDetailView,
    BookCheckInListView,
    BookCheckInUpdateView,
    BookCreateView,
    BookDetailView,
    BookUpdateView,
    EditionAutocomplete,
    EditionCreateView,
    EditionDetailView,
    EditionUpdateView,
    PublisherAutocomplete,
    PublisherCreateView,
    PublisherDetailView,
    ReadListView,
    WorkAutocomplete,
    WorkCreateView,
    WorkDetailView,
    WorkUpdateView,
)

app_name = "read"
urlpatterns = [
    # read
    path("recent/", view=ReadListView.as_view(), name="read_list"),
    # checkin
    path(
        "book/<int:book_id>/checkin/create/",
        BookCheckInCreateView.as_view(),
        name="book_checkin_create",
    ),
    path(
        "book/<int:book_id>/checkins/",
        view=BookCheckInAllListView.as_view(),
        name="book_checkin_all_list",
    ),
    path(
        "book/<int:book_id>/<str:username>/checkins/",
        view=BookCheckInListView.as_view(),
        name="book_checkin_list",
    ),
    path(
        "checkin/<int:pk>/", BookCheckInDetailView.as_view(), name="book_checkin_detail"
    ),
    path(
        "checkin/<int:pk>/update/",
        BookCheckInUpdateView.as_view(),
        name="book_checkin_update",
    ),
    path(
        "checkin/<int:pk>/delete/",
        BookCheckInDeleteView.as_view(),
        name="book_checkin_delete",
    ),
    # edition
    path("edition/create/", EditionCreateView.as_view(), name="edition_create"),
    path("edition/<int:pk>/", EditionDetailView.as_view(), name="edition_detail"),
    path(
        "edition/<int:pk>/update/", EditionUpdateView.as_view(), name="edition_update"
    ),
    # work
    path("work/create/", WorkCreateView.as_view(), name="work_create"),
    path("work/<int:pk>/", WorkDetailView.as_view(), name="work_detail"),
    path("work/<int:pk>/update/", WorkUpdateView.as_view(), name="work_update"),
    # book
    path("book/create/", BookCreateView.as_view(), name="book_create"),
    path("book/<int:pk>/", BookDetailView.as_view(), name="book_detail"),
    path("book/<int:pk>/update/", BookUpdateView.as_view(), name="book_update"),
    # publisher
    path("publisher/create/", PublisherCreateView.as_view(), name="publisher_create"),
    path("publisher/<int:pk>/", PublisherDetailView.as_view(), name="publisher_detail"),
    # autocomplete views
    path(
        "edition-autocomplete/",
        EditionAutocomplete.as_view(),
        name="edition-autocomplete",
    ),
    path("work-autocomplete/", WorkAutocomplete.as_view(), name="work-autocomplete"),
    path(
        "publisher-autocomplete/",
        PublisherAutocomplete.as_view(),
        name="publisher-autocomplete",
    ),
]
