from django.urls import path

from activity_feed.feeds import UserActivityFeed

from .views import (
    AccountDetailView,
    AccountUpdateView,
    FollowingListView,
    GenerateInvitationCodeView,
    InvitationRequestedSuccessView,
    InvitationRequestedView,
    PersonalActivityFeedView,
    RequestInvitationView,
    SignUpView,
    ap_actor,
    ap_inbox,
    app_password_list,
    delete_app_password,
    export_user_data,
    get_followed_usernames,
    get_user_tags,
    manage_bluesky_account,
    manage_mastodon_account,
    redirect_to_profile,
)

app_name = "accounts"
urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path(
        "generate_invitation_code/",
        GenerateInvitationCodeView.as_view(),
        name="generate_invitation_code",
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
    path(
        "get_followed_usernames/", get_followed_usernames, name="get_followed_usernames"
    ),
    path("get_user_tags/", get_user_tags, name="get_user_tags"),
    path("<str:username>/", view=AccountDetailView.as_view(), name="detail"),
    path(
        "<str:username>/feed/",
        view=PersonalActivityFeedView.as_view(),
        name="feed",
    ),
    path("<str:username>/feed/rss", UserActivityFeed(), name="user_activity_feed"),
    path(
        "<str:username>/following/",
        FollowingListView.as_view(),
        name="following_list",
    ),
    path("<str:username>/update/", view=AccountUpdateView.as_view(), name="update"),
    path("<str:username>/app-passwords/", app_password_list, name="app_password"),
    path(
        "<str:username>/app-passwords/delete/<int:pk>/",
        delete_app_password,
        name="delete_app_password",
    ),
    path(
        "<str:username>/bluesky/",
        manage_bluesky_account,
        name="bluesky",
    ),
    path(
        "<str:username>/mastodon/",
        manage_mastodon_account,
        name="mastodon",
    ),
    path("<str:username>/actor/", ap_actor, name="ap_actor"),
    path("<str:username>/inbox/", ap_inbox, name="ap_inbox"),
]
