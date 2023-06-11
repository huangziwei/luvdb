from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView

from .models import Activity, Follow


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


@login_required
def follow(request, user_id):
    user_to_follow = get_object_or_404(get_user_model(), id=user_id)
    Follow.objects.get_or_create(follower=request.user, followed=user_to_follow)
    return redirect("activity_feed:activity_feed")


@login_required
def unfollow(request, user_id):
    user_to_unfollow = get_object_or_404(get_user_model(), id=user_id)
    Follow.objects.filter(follower=request.user, followed=user_to_unfollow).delete()
    return redirect("activity_feed:activity_feed")
