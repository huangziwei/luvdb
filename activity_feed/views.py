from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView

from write.forms import ActivityFeedSayForm

from .models import Activity, Follow

User = get_user_model()


class ActivityFeedView(ListView):
    model = Activity
    template_name = "activity_feed/activity_feed.html"

    def get_queryset(self):
        user = self.request.user
        following_users = user.following.all().values_list("followed", flat=True)
        return (
            super()
            .get_queryset()
            .filter(user__in=list(following_users) + [user.id])
            .order_by("-timestamp")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["say_form"] = ActivityFeedSayForm()
        return context


@login_required
def follow(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)
    Follow.objects.get_or_create(follower=request.user, followed=user_to_follow)
    return redirect("accounts:detail", username=user_to_follow.username)


@login_required
def unfollow(request, user_id):
    # Get the user to be unfollowed
    user_to_unfollow = User.objects.get(id=user_id)

    # Get the follow relationship
    follow_relationship = Follow.objects.filter(
        follower=request.user, followed=user_to_unfollow
    )

    # If the follow relationship exists, delete it
    if follow_relationship.exists():
        # Get the follow relationship instance before deleting it
        follow_instance = follow_relationship.first()

        # Delete the follow relationship
        follow_relationship.delete()

        # Get the content type for the Follow model
        content_type = ContentType.objects.get_for_model(Follow)

        # Delete the corresponding activity
        Activity.objects.filter(
            user=request.user,
            activity_type="follow",
            content_type=content_type,
            object_id=follow_instance.id,
        ).delete()

    # Redirect to the unfollowed user's profile page
    return redirect("accounts:detail", username=user_to_unfollow.username)
