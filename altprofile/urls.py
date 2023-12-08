from django.urls import path

from altprofile.views import (
    AltProfileDetailView,
    AltProfileLoginView,
    AltProfileUpdateView,
    ApplyTemplateView,
    PreviewTemplateView,
)

urlpatterns = [
    path("login/", AltProfileLoginView.as_view(), name="altprofile_login"),
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
