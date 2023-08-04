import pytz
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import DeleteView, ListView

from entity.models import Person
from listen.models import Release
from play.models import Game
from read.models import Book
from watch.models import Movie, Series
from write.forms import ActivityFeedSayForm

from .models import Activity, Block, Follow

User = get_user_model()


class ActivityFeedView(LoginRequiredMixin, ListView):
    model = Activity
    template_name = "activity_feed/activity_feed.html"
    paginate_by = 50

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["say_form"] = ActivityFeedSayForm()
        context["feed_type"] = "public"
        context["no_citation_css"] = True

        # Get current month and day
        now = timezone.localtime(
            timezone.now(), pytz.timezone(self.request.user.timezone)
        )  # Use user's timezone
        current_month_day = now.strftime(".%m.%d")
        current_month_day_dash = now.strftime("-%m-%d")

        # Query for people born or died on this day
        born_today = Person.objects.filter(
            Q(birth_date__contains=current_month_day)
            | Q(birth_date__contains=current_month_day_dash)
        )
        died_today = Person.objects.filter(
            Q(death_date__contains=current_month_day)
            | Q(death_date__contains=current_month_day_dash)
        )

        # Calculate age at birth or death
        for person in born_today:
            birth_year = int(
                person.birth_date.split("-" if "-" in person.birth_date else ".")[0]
            )
            person.since = now.year - birth_year

        for person in died_today:
            death_year = int(
                person.death_date.split("-" if "-" in person.death_date else ".")[0]
            )
            person.since = now.year - death_year

        context["born_today"] = born_today
        context["died_today"] = died_today

        # Query for books published on this day
        books_published_today = Book.objects.filter(
            Q(publication_date__contains=current_month_day)
            | Q(publication_date__contains=current_month_day_dash)
        )

        # Calculate years since publication
        for book in books_published_today:
            publication_year = int(
                book.publication_date.split(
                    "-" if "-" in book.publication_date else "."
                )[0]
            )
            book.since = now.year - publication_year
            book.authors = book.bookrole_set.filter(role__name="Author").values(
                "person__name", "alt_name"
            )

        context["books_published_today"] = books_published_today

        # Query for movies released on this day
        movies_released_today = Movie.objects.filter(
            Q(release_date__contains=current_month_day)
            | Q(release_date__contains=current_month_day_dash)
        )

        # Calculate years since release
        for movie in movies_released_today:
            release_year = int(
                movie.release_date.split("-" if "-" in movie.release_date else ".")[0]
            )
            movie.since = now.year - release_year

        context["movies_released_today"] = movies_released_today

        # Query for series released on this day
        series_released_today = Series.objects.filter(
            Q(release_date__contains=current_month_day)
            | Q(release_date__contains=current_month_day_dash)
        )

        # Calculate years since release
        for serie in series_released_today:
            release_year = int(
                serie.release_date.split("-" if "-" in serie.release_date else ".")[0]
            )
            serie.since = now.year - release_year

        context["series_released_today"] = series_released_today

        # Query for music released on this day
        music_released_today = Release.objects.filter(
            Q(release_date__contains=current_month_day)
            | Q(release_date__contains=current_month_day_dash)
        )

        # Calculate years since release
        for music in music_released_today:
            release_year = int(
                music.release_date.split("-" if "-" in music.release_date else ".")[0]
            )
            music.since = now.year - release_year

        context["music_released_today"] = music_released_today

        # Query for music released on this day
        games_released_today = Game.objects.filter(
            Q(release_date__contains=current_month_day)
            | Q(release_date__contains=current_month_day_dash)
        )

        # Calculate years since release
        for game in games_released_today:
            release_year = int(
                game.release_date.split("-" if "-" in game.release_date else ".")[0]
            )
            game.since = now.year - release_year

        context["games_released_today"] = games_released_today

        return context

    def post(self, request, *args, **kwargs):
        form = ActivityFeedSayForm(request.POST)
        if form.is_valid():
            say = form.save(commit=False)
            say.user = request.user
            say.save()
        return redirect("activity_feed:activity_feed")

    def get_queryset(self):
        user = self.request.user
        following_users = user.following.all().values_list("followed", flat=True)
        return (
            super()
            .get_queryset()
            .filter(user__in=list(following_users) + [user.id])
            .order_by("-timestamp")
        )


class ActivityFeedDeleteView(LoginRequiredMixin, DeleteView):
    model = Activity
    template_name = "activity_feed/activity_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy("activity_feed:activity_feed")


@login_required
def follow(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)

    # check if the logged-in user is blocked by the user they're trying to follow
    if Block.objects.filter(blocker=user_to_follow, blocked=request.user).exists():
        messages.error(
            request, "You have been blocked by this user and cannot follow them."
        )
        return redirect("accounts:detail", username=user_to_follow.username)

    # check if the logged-in user has blocked the user they're trying to follow
    if Block.objects.filter(blocker=request.user, blocked=user_to_follow).exists():
        messages.error(request, "You have blocked this user. Unblock them to follow.")
        return redirect("accounts:detail", username=user_to_follow.username)

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


@login_required
def block_view(request, user_id):
    user_to_block = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        Block.objects.create(blocker=request.user, blocked=user_to_block)

        # If the blocker is following the blocked user, remove that follow relationship
        Follow.objects.filter(follower=request.user, followed=user_to_block).delete()

        # If the blocked user is following the blocker, remove that follow relationship
        Follow.objects.filter(follower=user_to_block, followed=request.user).delete()

        # You might also want to remove any activities related to the blocked user.
        content_type = ContentType.objects.get_for_model(User)
        Activity.objects.filter(
            user=request.user,
            content_type=content_type,
            object_id=user_to_block.id,
        ).delete()

        return redirect("accounts:detail", username=user_to_block.username)


@login_required
def unblock_view(request, user_id):
    user_to_unblock = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        Block.objects.filter(blocker=request.user, blocked=user_to_unblock).delete()

        # Depending on your requirements, you may want to re-establish follow relationships here.

        return redirect("accounts:detail", username=user_to_unblock.username)
