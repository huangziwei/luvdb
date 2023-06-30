from django.urls import path

from .views import (
    LabelAutocomplete,
    LabelCreateView,
    LabelDetailView,
    WorkCreateView,
    WorkDetailView,
    WorkUpdateView,
)

app_name = "listen"
urlpatterns = [
    # label
    path("label/create/", LabelCreateView.as_view(), name="label_create"),
    path("label/<int:pk>/", LabelDetailView.as_view(), name="label_detail"),
    # work
    path("work/create/", WorkCreateView.as_view(), name="work_create"),
    path("work/<int:pk>/", WorkDetailView.as_view(), name="work_detail"),
    path("work/<int:pk>/update/", WorkUpdateView.as_view(), name="work_update"),
    # autocomplete views
    path(
        "label-autocomplete/",
        LabelAutocomplete.as_view(),
        name="label-autocomplete",
    ),
]
