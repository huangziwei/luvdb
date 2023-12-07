from django.urls import path

from accounts.views import AltAccountDetailView

urlpatterns = [
    path(
        "@<str:username>/",
        AltAccountDetailView.as_view(),
        name="alt_account_detail",
    ),
]
