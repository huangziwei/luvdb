from django.urls import path

from .views import (
    BookCreateView,
    BookDetailView,
    BookUpdateView,
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
    path("work-autocomplete/", WorkAutocomplete.as_view(), name="work-autocomplete"),
    path(
        "publisher-autocomplete/",
        PublisherAutocomplete.as_view(),
        name="publisher-autocomplete",
    ),
]
