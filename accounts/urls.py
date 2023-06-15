from django.urls import path

from .views import (
    AccountDetailView,
    AccountUpdateView,
    GenerateInvitationCodeView,
    PersonalActivityFeedView,
    SignUpView,
    redirect_to_profile,
    search_view,
)

app_name = "accounts"
urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("update/", view=AccountUpdateView.as_view(), name="update"),
    path(
        "generate_invitation_code/",
        GenerateInvitationCodeView.as_view(),
        name="generate_invitation_code",
    ),
    path("search/", search_view, name="search"),
    path("people/<str:username>/", view=AccountDetailView.as_view(), name="detail"),
    path(
        "people/<str:username>/feed",
        view=PersonalActivityFeedView.as_view(),
        name="feed",
    ),
    path("profile", view=redirect_to_profile, name="profile"),
]
