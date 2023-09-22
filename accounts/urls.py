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
    get_followed_usernames,
    get_user_tags,
    redirect_to_profile,
    search_view,
)

app_name = "accounts"
urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path(
        "generate_invitation_code/",
        GenerateInvitationCodeView.as_view(),
        name="generate_invitation_code",
    ),
    path("search/", search_view, name="search"),
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
    path(
        "get_followed_usernames/", get_followed_usernames, name="get_followed_usernames"
    ),
    path("get_user_tags/", get_user_tags, name="get_user_tags"),
    path("<str:username>/", view=AccountDetailView.as_view(), name="detail"),
    path(
        "<str:username>/feed",
        view=PersonalActivityFeedView.as_view(),
        name="feed",
    ),
    path("<str:username>/feed/rss", UserActivityFeed(), name="user_activity_feed"),
    path(
        "<str:username>/following/",
        FollowingListView.as_view(),
        name="following_list",
    ),
    path(
        "<str:username>/followers/",
        FollowerListView.as_view(),
        name="follower_list",
    ),
    path("<str:username>/update/", view=AccountUpdateView.as_view(), name="update"),
]
