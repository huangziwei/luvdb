from django.urls import path

from activity_feed.feeds import UserActivityFeed

from .views import (
    AccountDetailView,
    AccountUpdateView,
    FollowerListView,
    FollowingListView,
    GenerateInvitationCodeView,
    InvitationRequestedSuccessView,
    InvitationRequestedView,
    PersonalActivityFeedView,
    RequestInvitationView,
    SignUpView,
    export_user_data,
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
    path("u/<str:username>/", view=AccountDetailView.as_view(), name="detail"),
    path(
        "u/<str:username>/feed",
        view=PersonalActivityFeedView.as_view(),
        name="feed",
    ),
    path("u/<str:username>/feed/rss", UserActivityFeed(), name="user_activity_feed"),
    path(
        "u/<str:username>/following/",
        FollowingListView.as_view(),
        name="following_list",
    ),
    path(
        "u/<str:username>/followers/",
        FollowerListView.as_view(),
        name="follower_list",
    ),
    path("profile", view=redirect_to_profile, name="profile"),
    path("exportdata/", export_user_data, name="export_user_data"),
    path(
        "request-invitation/",
        RequestInvitationView.as_view(),
        name="request_invitation",
    ),
    path(
        "invitation-requested/<str:email>/",
        InvitationRequestedView.as_view(),
        name="invitation_requested",
    ),
    path(
        "invitation-requested-success/",
        InvitationRequestedSuccessView.as_view(),
        name="invitation_requested_success",
    ),
]
