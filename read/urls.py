from django.urls import path

from .views import (
    BookAutoComplete,
    BookCreateView,
    BookDetailView,
    BookGroupCreateView,
    BookGroupDetailView,
    BookGroupHistoryView,
    BookGroupUpdateView,
    BookHistoryView,
    BookSeriesCreateView,
    BookSeriesDetailView,
    BookSeriesHistoryView,
    BookSeriesUpdateView,
    BookUpdateView,
    GenericCheckInAllListView,
    GenericCheckInListView,
    GenreAutocomplete,
    GenreDetailView,
    InstanceAutocomplete,
    InstanceCreateView,
    InstanceDetailView,
    InstanceHistoryView,
    InstanceUpdateView,
    IssueCreateView,
    IssueDetailView,
    IssueHistoryView,
    IssueUpdateView,
    LanguageAutocomplete,
    PeriodicalCreateView,
    PeriodicalDetailView,
    PeriodicalHistoryView,
    PeriodicalUpdateView,
    ReadListAllView,
    ReadListView,
    WorkAutocomplete,
    WorkCreateView,
    WorkDetailView,
    WorkHistoryView,
    WorkUpdateView,
)

app_name = "read"
urlpatterns = [
    # read
    path("recent/", view=ReadListView.as_view(), name="read_list"),
    path("all/", view=ReadListAllView.as_view(), name="read_list_all"),
    # checkin
    path(
        "book/<int:object_id>/checkins/",
        view=GenericCheckInAllListView.as_view(),
        kwargs={"model_name": "book"},
        name="book_checkin_all_list",
    ),
    path(
        "book/<int:object_id>/checkins/@<str:username>/",
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
        "periodical/<int:periodical_id>/issue/<int:object_id>/checkins/@<str:username>/",
        view=GenericCheckInListView.as_view(),
        kwargs={"model_name": "issue"},
        name="issue_checkin_list",
    ),
    # instance
    path("instance/create/", InstanceCreateView.as_view(), name="instance_create"),
    path(
        "instance/create/<int:work_id>/",
        InstanceCreateView.as_view(),
        name="instance_create_with_work",
    ),
    path("instance/<int:pk>/", InstanceDetailView.as_view(), name="instance_detail"),
    path(
        "instance/<int:pk>/update/",
        InstanceUpdateView.as_view(),
        name="instance_update",
    ),
    path(
        "instance/<int:pk>/history/",
        InstanceHistoryView.as_view(),
        name="instance_history",
    ),
    # work
    path("work/create/", WorkCreateView.as_view(), name="work_create"),
    path("work/<int:pk>/", WorkDetailView.as_view(), name="work_detail"),
    path("work/<int:pk>/update/", WorkUpdateView.as_view(), name="work_update"),
    path("work/<int:pk>/history/", WorkHistoryView.as_view(), name="work_history"),
    # book
    path("book/create/", BookCreateView.as_view(), name="book_create"),
    path(
        "book/create/<int:instance_id>/",
        BookCreateView.as_view(),
        name="book_create_with_instance",
    ),
    path("book/<int:pk>/", BookDetailView.as_view(), name="book_detail"),
    path("book/<int:pk>/update/", BookUpdateView.as_view(), name="book_update"),
    path("book/<int:pk>/history/", BookHistoryView.as_view(), name="book_history"),
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
    path(
        "periodical/<int:pk>/history/",
        PeriodicalHistoryView.as_view(),
        name="periodical_history",
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
    path(
        "periodical/<int:periodical_id>/issue/<int:pk>/history/",
        IssueHistoryView.as_view(),
        name="issue_history",
    ),
    # autocomplete views
    path("book-autocomplete/", BookAutoComplete.as_view(), name="book-autocomplete"),
    path(
        "instance-autocomplete/",
        InstanceAutocomplete.as_view(),
        name="instance-autocomplete",
    ),
    path("work-autocomplete/", WorkAutocomplete.as_view(), name="work-autocomplete"),
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
    path(
        "series/<int:pk>/history/",
        BookSeriesHistoryView.as_view(),
        name="series_history",
    ),
    # genre
    path("genre/<slug:slug>/", GenreDetailView.as_view(), name="genre_detail"),
    path("genre-autocomplete/", GenreAutocomplete.as_view(), name="genre-autocomplete"),
    # book group
    path(
        "bookgroup/create/",
        BookGroupCreateView.as_view(),
        name="bookgroup_create",
    ),
    path(
        "bookgroup/<int:pk>/",
        BookGroupDetailView.as_view(),
        name="bookgroup_detail",
    ),
    path(
        "bookgroup/<int:pk>/update/",
        BookGroupUpdateView.as_view(),
        name="bookgroup_update",
    ),
    path(
        "bookgroup/<int:pk>/history/",
        BookGroupHistoryView.as_view(),
        name="bookgroup_history",
    ),
]
