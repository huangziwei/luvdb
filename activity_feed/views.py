from calendar import Calendar

import pytz
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Min, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import DeleteView, ListView

from entity.models import Creator
from listen.models import Release
from play.models import Game, GameReleaseDate
from read.models import Book
from watch.models import Movie, MovieReleaseDate, Series
from write.forms import ActivityFeedSayForm

from .models import Activity, Block, Follow

User = get_user_model()


class ActivityFeedView(LoginRequiredMixin, ListView):
    model = Activity
    template_name = "activity_feed/activity_feed.html"
    paginate_by = 20

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
        born_today = Creator.objects.filter(
            Q(birth_date__contains=current_month_day)
            | Q(birth_date__contains=current_month_day_dash),
            creator_type="person",
        ).order_by("birth_date")

        died_today = Creator.objects.filter(
            Q(death_date__contains=current_month_day)
            | Q(death_date__contains=current_month_day_dash),
            creator_type="person",
        ).order_by("death_date")

        # Query for groups formed or dissolved on this day
        formed_today = Creator.objects.filter(
            Q(birth_date__contains=current_month_day)
            | Q(birth_date__contains=current_month_day_dash),
            creator_type="group",
        ).order_by("birth_date")

        dissolved_today = Creator.objects.filter(
            Q(death_date__contains=current_month_day)
            | Q(death_date__contains=current_month_day_dash),
            creator_type="group",
        ).order_by("death_date")

        # Calculate age at birth or death for persons
        for creator in born_today:
            birth_year = int(
                creator.birth_date.split("-" if "-" in creator.birth_date else ".")[0]
            )
            creator.since = now.year - birth_year

        for creator in died_today:
            death_year = int(
                creator.death_date.split("-" if "-" in creator.death_date else ".")[0]
            )
            creator.since = now.year - death_year

        # Calculate age at formation or dissolution for groups
        for creator in formed_today:
            formation_year = int(
                creator.birth_date.split("-" if "-" in creator.birth_date else ".")[0]
            )
            creator.since = now.year - formation_year

        for creator in dissolved_today:
            dissolution_year = int(
                creator.death_date.split("-" if "-" in creator.death_date else ".")[0]
            )
            creator.since = now.year - dissolution_year

        context["born_today"] = born_today
        context["died_today"] = died_today
        context["formed_today"] = formed_today
        context["dissolved_today"] = dissolved_today

        # Query for books published on this day
        books_published_today = Book.objects.filter(
            Q(publication_date__contains=current_month_day)
            | Q(publication_date__contains=current_month_day_dash)
        ).order_by("publication_date")

        # Calculate years since publication
        for book in books_published_today:
            publication_year = int(
                book.publication_date.split(
                    "-" if "-" in book.publication_date else "."
                )[0]
            )
            book.since = now.year - publication_year
            book.authors = book.bookrole_set.filter(role__name="Author").values(
                "creator__name", "alt_name"
            )

        context["books_published_today"] = books_published_today

        # Query for movies released on this day
        movies_released_today = (
            MovieReleaseDate.objects.values("movie")
            .annotate(earliest_release=Min("release_date"))
            .filter(
                Q(earliest_release__contains=current_month_day)
                | Q(earliest_release__contains=current_month_day_dash)
            )
            .order_by("earliest_release", "movie")
        )

        # Create a dictionary to hold the movies and their years since release
        movies_dict = {}

        # Calculate years since release
        for release in movies_released_today:
            release_year = int(
                release["earliest_release"].split(
                    "-" if "-" in release["earliest_release"] else "."
                )[0]
            )
            since = now.year - release_year

            # Retrieve the actual Movie object
            movie = Movie.objects.get(pk=release["movie"])
            movie.earliest_release = release["earliest_release"]

            # Add or update the movie in the dictionary
            if movie not in movies_dict:
                movie.since = since
                movies_dict[movie] = movie
            else:
                # Update the 'since' value if needed
                if movies_dict[movie].since > since:
                    movies_dict[movie].since = since

        # Convert the dictionary values to a list
        movies_released_today_list = list(movies_dict.values())

        context["movies_released_today"] = movies_released_today_list

        # Query for series released on this day
        series_released_today = Series.objects.filter(
            Q(release_date__contains=current_month_day)
            | Q(release_date__contains=current_month_day_dash)
        ).order_by("release_date")

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
        ).order_by("release_date")

        # Calculate years since release
        for music in music_released_today:
            release_year = int(
                music.release_date.split("-" if "-" in music.release_date else ".")[0]
            )
            music.since = now.year - release_year

        context["music_released_today"] = music_released_today

        # Query for games with releases on this day
        games_released_today = (
            GameReleaseDate.objects.values("game")
            .annotate(earliest_release=Min("release_date"))
            .filter(
                Q(earliest_release__contains=current_month_day)
                | Q(earliest_release__contains=current_month_day_dash)
            )
            .order_by("earliest_release", "game")
        )

        # Create a dictionary to hold the games and their years since release
        games_dict = {}

        # Calculate years since release
        for release in games_released_today:
            release_year = int(
                release["earliest_release"].split(
                    "-" if "-" in release["earliest_release"] else "."
                )[0]
            )
            since = now.year - release_year

            # Retrieve the actual Game object
            game = Game.objects.get(pk=release["game"])
            game.earliest_release = release["earliest_release"]

            # Add or update the game in the dictionary
            if game not in games_dict:
                game.since = since
                games_dict[game] = game
            else:
                # Update the 'since' value if needed
                if games_dict[game].since > since:
                    games_dict[game].since = since

        # Convert the dictionary values to a list
        games_released_today_list = list(games_dict.values())

        context["games_released_today"] = games_released_today_list

        # Add calendar context
        cal = Calendar()
        today = timezone.localtime(timezone.now()).date()
        context["calendar"] = cal.monthdayscalendar(today.year, today.month)
        context["current_date"] = now.strftime("%Y-%m-%d")

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


class CalendarActivityFeedView(ActivityFeedView):
    def get_queryset(self):
        selected_date = self.kwargs.get("selected_date")
        try:
            filter_date = timezone.datetime.strptime(selected_date, "%Y-%m-%d").date()
        except ValueError:
            # Handle date parsing error
            return super().get_queryset()

        user = self.request.user
        following_users = user.following.all().values_list("followed", flat=True)
        return (
            super()
            .get_queryset()
            .filter(
                user__in=list(following_users) + [user.id], timestamp__date=filter_date
            )
            .order_by("-timestamp")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["say_form"] = ActivityFeedSayForm()
        context["feed_type"] = "public"
        context["no_citation_css"] = True
        # Add date to the context
        selected_date_str = self.kwargs.get("selected_date")

        # Convert selected_date_str to a datetime object, using the user's timezone
        selected_date = timezone.datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        selected_datetime = timezone.make_aware(
            timezone.datetime.combine(selected_date, timezone.datetime.min.time())
        )
        selected_datetime = timezone.localtime(
            selected_datetime, pytz.timezone(self.request.user.timezone)
        )

        # Get month and day of selected_date
        selected_month_day = selected_datetime.strftime(".%m.%d")
        selected_month_day_dash = selected_datetime.strftime("-%m-%d")

        # Query for people born or died on this day
        born_today = Creator.objects.filter(
            Q(birth_date__contains=selected_month_day)
            | Q(birth_date__contains=selected_month_day_dash),
            creator_type="person",
        ).order_by("birth_date")

        died_today = Creator.objects.filter(
            Q(death_date__contains=selected_month_day)
            | Q(death_date__contains=selected_month_day_dash),
            creator_type="person",
        ).order_by("death_date")

        # Query for groups formed or dissolved on this day
        formed_today = Creator.objects.filter(
            Q(birth_date__contains=selected_month_day)
            | Q(birth_date__contains=selected_month_day_dash),
            creator_type="group",
        ).order_by("birth_date")

        dissolved_today = Creator.objects.filter(
            Q(death_date__contains=selected_month_day)
            | Q(death_date__contains=selected_month_day_dash),
            creator_type="group",
        ).order_by("death_date")

        # Calculate age at birth or death for persons
        for creator in born_today:
            birth_year = int(
                creator.birth_date.split("-" if "-" in creator.birth_date else ".")[0]
            )
            creator.since = selected_datetime.year - birth_year

        for creator in died_today:
            death_year = int(
                creator.death_date.split("-" if "-" in creator.death_date else ".")[0]
            )
            creator.since = selected_datetime.year - death_year

        # Calculate age at formation or dissolution for groups
        for creator in formed_today:
            formation_year = int(
                creator.birth_date.split("-" if "-" in creator.birth_date else ".")[0]
            )
            creator.since = selected_datetime.year - formation_year

        for creator in dissolved_today:
            dissolution_year = int(
                creator.death_date.split("-" if "-" in creator.death_date else ".")[0]
            )
            creator.since = selected_datetime.year - dissolution_year

        context["born_today"] = born_today
        context["died_today"] = died_today
        context["formed_today"] = formed_today
        context["dissolved_today"] = dissolved_today

        # Query for books published on this day
        books_published_today = Book.objects.filter(
            Q(publication_date__contains=selected_month_day)
            | Q(publication_date__contains=selected_month_day_dash)
        ).order_by("publication_date")

        # Calculate years since publication
        for book in books_published_today:
            publication_year = int(
                book.publication_date.split(
                    "-" if "-" in book.publication_date else "."
                )[0]
            )
            book.since = selected_datetime.year - publication_year
            book.authors = book.bookrole_set.filter(role__name="Author").values(
                "creator__name", "alt_name"
            )

        context["books_published_today"] = books_published_today

        movies_released_today = (
            MovieReleaseDate.objects.values("movie")
            .annotate(earliest_release=Min("release_date"))
            .filter(
                Q(earliest_release__contains=selected_month_day)
                | Q(earliest_release__contains=selected_month_day_dash)
            )
            .order_by("earliest_release", "movie")
        )

        # Create a dictionary to hold the movies and their years since release
        movies_dict = {}

        # Calculate years since release
        for release in movies_released_today:
            release_year = int(
                release["earliest_release"].split(
                    "-" if "-" in release["earliest_release"] else "."
                )[0]
            )
            since = selected_datetime.year - release_year

            # Retrieve the actual Movie object
            movie = Movie.objects.get(pk=release["movie"])
            movie.earliest_release = release["earliest_release"]

            # Add or update the movie in the dictionary
            if movie not in movies_dict:
                movie.since = since
                movies_dict[movie] = movie
            else:
                # Update the 'since' value if needed
                if movies_dict[movie].since > since:
                    movies_dict[movie].since = since

        # Convert the dictionary values to a list
        movies_released_today_list = list(movies_dict.values())

        context["movies_released_today"] = movies_released_today_list

        # Query for series released on this day
        series_released_today = Series.objects.filter(
            Q(release_date__contains=selected_month_day)
            | Q(release_date__contains=selected_month_day_dash)
        ).order_by("release_date")

        # Calculate years since release
        for serie in series_released_today:
            release_year = int(
                serie.release_date.split("-" if "-" in serie.release_date else ".")[0]
            )
            serie.since = selected_datetime.year - release_year

        context["series_released_today"] = series_released_today

        # Query for music released on this day
        music_released_today = Release.objects.filter(
            Q(release_date__contains=selected_month_day)
            | Q(release_date__contains=selected_month_day_dash)
        ).order_by("release_date")

        # Calculate years since release
        for music in music_released_today:
            release_year = int(
                music.release_date.split("-" if "-" in music.release_date else ".")[0]
            )
            music.since = selected_datetime.year - release_year

        context["music_released_today"] = music_released_today

        # Query for games with releases on this day
        games_released_today = (
            GameReleaseDate.objects.values("game")
            .annotate(earliest_release=Min("release_date"))
            .filter(
                Q(earliest_release__contains=selected_month_day)
                | Q(earliest_release__contains=selected_month_day_dash)
            )
            .order_by("earliest_release", "game")
        )

        # Create a dictionary to hold the games and their years since release
        games_dict = {}

        # Calculate years since release
        for release in games_released_today:
            release_year = int(
                release["earliest_release"].split(
                    "-" if "-" in release["earliest_release"] else "."
                )[0]
            )
            since = selected_date.year - release_year

            # Retrieve the actual Game object
            game = Game.objects.get(pk=release["game"])
            game.earliest_release = release["earliest_release"]

            # Add or update the game in the dictionary
            if game not in games_dict:
                game.since = since
                games_dict[game] = game
            else:
                # Update the 'since' value if needed
                if games_dict[game].since > since:
                    games_dict[game].since = since

        # Convert the dictionary values to a list
        games_released_today_list = list(games_dict.values())

        context["games_released_today"] = games_released_today_list

        # Add calendar context
        cal = Calendar()
        today = timezone.localtime(timezone.now()).date()
        context["calendar"] = cal.monthdayscalendar(today.year, today.month)
        context["selected_date"] = selected_datetime.strftime("%Y-%m-%d")

        return context
