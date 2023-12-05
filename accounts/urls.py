from django.urls import path

from activity_feed.feeds import UserActivityFeed
from discover.views import DiscoverLikedView

from .views import (
    AccountDetailView,
    AccountUpdateView,
    FollowingListView,
    GenerateInvitationCodeView,
    InvitationRequestedSuccessView,
    InvitationRequestedView,
    PersonalActivityFeedView,
    RequestInvitationView,
    app_password_list,
    delete_app_password,
    export_user_data,
    get_followed_usernames,
    get_user_tags,
    manage_crossposters,
    redirect_to_profile,
)

app_name = "accounts"
urlpatterns = [
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
    path("<str:username>/liked/", DiscoverLikedView.as_view(), name="liked"),
    path("<str:username>/update/", view=AccountUpdateView.as_view(), name="update"),
    path("<str:username>/app-passwords/", app_password_list, name="app_password"),
    path(
        "<str:username>/app-passwords/delete/<int:pk>/",
        delete_app_password,
        name="delete_app_password",
    ),
    path(
        "<str:username>/crossposters/",
        manage_crossposters,
        name="crossposters",
    ),
]
