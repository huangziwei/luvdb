from django.urls import path

from activity_feed.feeds import UserActivityFeed
from discover.views import DiscoverLikedView

from .views import (
    AccountDetailView,
    AccountUpdateView,
    FollowingListView,
    InvitationRequestedSuccessView,
    InvitationRequestedView,
    ManageInvitationsView,
    PersonalActivityFeedView,
    RequestInvitationView,
    app_password_list,
    deactivate_account,
    delete_app_password,
    export_user_data,
    generate_qr_code,
    manage_crossposters,
)

app_name = "accounts"
urlpatterns = [
    path("<str:username>/export/", export_user_data, name="export_user_data"),
    path(
        "<str:username>/manage_invitations/",
        ManageInvitationsView.as_view(),
        name="manage_invitations",
    ),
    path(
        "<str:username>/invite_code/<str:invite_code>/",
        generate_qr_code,
        name="qr_code",
    ),
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
    path(
        "<str:username>/deactivate/",
        deactivate_account,
        name="deactivate_account",
    ),
]
