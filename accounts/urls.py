from django.urls import path

from .views import (
    AccountDetailView,
    AccountUpdateView,
    FollowerListView,
    FollowingListView,
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
    path(
        "people/<str:username>/following/",
        FollowingListView.as_view(),
        name="following_list",
    ),
    path(
        "people/<str:username>/followers/",
        FollowerListView.as_view(),
        name="follower_list",
    ),
    path("profile", view=redirect_to_profile, name="profile"),
]
