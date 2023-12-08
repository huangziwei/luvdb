from django.conf import settings
from django.shortcuts import redirect
from django.urls import include, path, re_path

from altprofile.views import (
    AltProfileDetailView,
    AltProfileUpdateView,
    ApplyTemplateView,
    PreviewTemplateView,
)

urlpatterns = [
    path(
        "@<str:username>/",
        AltProfileDetailView.as_view(),
        name="altprofile_detail",
    ),
    path(
        "@<str:username>/update/",
        AltProfileUpdateView.as_view(),
        name="altprofile_update",
    ),
    path("apply-template/", ApplyTemplateView.as_view(), name="apply_template"),
    path(
        "preview-template/<int:template_id>/",
        PreviewTemplateView.as_view(),
        name="preview_template",
    ),
]
