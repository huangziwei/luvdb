from django.urls import path

from .views import (
    BookCreateView,
    BookDetailView,
    BookSeriesCreateView,
    BookSeriesDetailView,
    BookSeriesUpdateView,
    BookUpdateView,
    GenericCheckInAllListView,
    GenericCheckInListView,
    GenericCheckInUserListView,
    GenreAutocomplete,
    GenreDetailView,
    InstanceAutocomplete,
    InstanceCreateView,
    InstanceDetailView,
    InstanceUpdateView,
    IssueCreateView,
    IssueDetailView,
    IssueUpdateView,
    LanguageAutocomplete,
    PeriodicalCreateView,
    PeriodicalDetailView,
    PeriodicalUpdateView,
    PublisherAutocomplete,
    PublisherCreateView,
    PublisherDetailView,
    PublisherUpdateView,
    ReadCheckInCreateView,
    ReadCheckInDeleteView,
    ReadCheckInDetailView,
    ReadCheckInUpdateView,
    ReadListAllView,
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
    path("all/", view=ReadListAllView.as_view(), name="read_list_all"),
    # checkin
    path(
        "book/<int:book_id>/checkin/create/",
        ReadCheckInCreateView.as_view(),
        name="read_checkin_create",
    ),
    path(
        "book/<int:object_id>/checkins/",
        view=GenericCheckInAllListView.as_view(),
        kwargs={"model_name": "book"},
        name="book_checkin_all_list",
    ),
    path(
        "book/<int:object_id>/<str:username>/checkins/",
        view=GenericCheckInListView.as_view(),
        kwargs={"model_name": "book"},
        name="book_checkin_list",
    ),
    path(
        "periodical/<int:periodical_id>/issue/<int:object_id>/checkins/",
        view=GenericCheckInAllListView.as_view(),
        kwargs={"model_name": "issue"},
        name="issue_checkin_all_list",
    ),
    path(
        "periodical/<int:periodical_id>/issue/<int:object_id>/<str:username>/checkins/",
        view=GenericCheckInListView.as_view(),
        kwargs={"model_name": "issue"},
        name="issue_checkin_list",
    ),
    path(
        "checkin/<int:pk>/", ReadCheckInDetailView.as_view(), name="read_checkin_detail"
    ),
    path(
        "checkin/<int:pk>/update/",
        ReadCheckInUpdateView.as_view(),
        name="read_checkin_update",
    ),
    path(
        "checkin/<int:pk>/delete/",
        ReadCheckInDeleteView.as_view(),
        name="read_checkin_delete",
    ),
    path(
        "<str:username>/checkins/",
        view=GenericCheckInUserListView.as_view(),
        name="read_checkin_user_list",
    ),
    # instance
    path("instance/create/", InstanceCreateView.as_view(), name="instance_create"),
    path("instance/<int:pk>/", InstanceDetailView.as_view(), name="instance_detail"),
    path(
        "instance/<int:pk>/update/",
        InstanceUpdateView.as_view(),
        name="instance_update",
    ),
    # work
    path("work/create/", WorkCreateView.as_view(), name="work_create"),
    path("work/<int:pk>/", WorkDetailView.as_view(), name="work_detail"),
    path("work/<int:pk>/update/", WorkUpdateView.as_view(), name="work_update"),
    # book
    path("book/create/", BookCreateView.as_view(), name="book_create"),
    path("book/<int:pk>/", BookDetailView.as_view(), name="book_detail"),
    path("book/<int:pk>/update/", BookUpdateView.as_view(), name="book_update"),
    # periodical
    path(
        "periodical/create/", PeriodicalCreateView.as_view(), name="periodical_create"
    ),
    path(
        "periodical/<int:pk>/", PeriodicalDetailView.as_view(), name="periodical_detail"
    ),
    path(
        "periodical/<int:pk>/update/",
        PeriodicalUpdateView.as_view(),
        name="periodical_update",
    ),
    # issue of a periodical
    path(
        "periodical/<int:periodical_id>/issue/create/",
        IssueCreateView.as_view(),
        name="issue_create",
    ),
    path(
        "periodical/<int:periodical_id>/issue/<int:pk>/",
        IssueDetailView.as_view(),
        name="issue_detail",
    ),
    path(
        "periodical/<int:periodical_id>/issue/<int:pk>/update/",
        IssueUpdateView.as_view(),
        name="issue_update",
    ),
    # publisher
    path("publisher/create/", PublisherCreateView.as_view(), name="publisher_create"),
    path("publisher/<int:pk>/", PublisherDetailView.as_view(), name="publisher_detail"),
    path(
        "publisher/<int:pk>/update/",
        PublisherUpdateView.as_view(),
        name="publisher_update",
    ),
    # autocomplete views
    path(
        "instance-autocomplete/",
        InstanceAutocomplete.as_view(),
        name="instance-autocomplete",
    ),
    path("work-autocomplete/", WorkAutocomplete.as_view(), name="work-autocomplete"),
    path(
        "publisher-autocomplete/",
        PublisherAutocomplete.as_view(),
        name="publisher-autocomplete",
    ),
    path(
        "language-autocomplete/",
        LanguageAutocomplete.as_view(),
        name="language-autocomplete",
    ),
    # series
    path("series/create/", BookSeriesCreateView.as_view(), name="series_create"),
    path("series/<int:pk>/", BookSeriesDetailView.as_view(), name="series_detail"),
    path(
        "series/<int:pk>/update/", BookSeriesUpdateView.as_view(), name="series_update"
    ),
    # genre
    path("genre/<slug:slug>/", GenreDetailView.as_view(), name="genre_detail"),
    path("genre-autocomplete/", GenreAutocomplete.as_view(), name="genre-autocomplete"),
]
