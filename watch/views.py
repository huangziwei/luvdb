from collections import defaultdict
from datetime import timedelta
from typing import Any

from dal import autocomplete
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count, F, Max, Min, OuterRef, Q, Subquery
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from django_ratelimit.decorators import ratelimit

from activity_feed.models import Block
from discover.views import user_has_upvoted
from entity.views import HistoryViewMixin
from write.forms import CommentForm, RepostForm
from write.models import Comment, ContentInList
from write.utils_formatting import check_required_js

from .forms import (
    CollectionForm,
    ContentInCollection,
    ContentInCollectionFormSet,
    EpisodeCastFormSet,
    EpisodeForm,
    EpisodeRoleFormSet,
    MovieCastFormSet,
    MovieForm,
    MovieReleaseDateFormSet,
    MovieRoleFormSet,
    SeriesForm,
    SeriesRoleFormSet,
    WatchCheckInForm,
)
from .models import (
    Collection,
    Episode,
    EpisodeCast,
    EpisodeRole,
    Genre,
    Movie,
    Series,
    WatchCheckIn,
)

User = get_user_model()


class MovieCreateView(LoginRequiredMixin, CreateView):
    model = Movie
    form_class = MovieForm
    template_name = "watch/movie_create.html"

    def get_success_url(self):
        return reverse_lazy("watch:movie_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["movieroles"] = MovieRoleFormSet(
                self.request.POST, instance=self.object
            )
            data["moviecasts"] = MovieCastFormSet(
                self.request.POST, instance=self.object
            )
            data["regionreleasedates"] = MovieReleaseDateFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["movieroles"] = MovieRoleFormSet(instance=self.object)
            data["moviecasts"] = MovieCastFormSet(instance=self.object)
            data["regionreleasedates"] = MovieReleaseDateFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        movierole = context["movieroles"]
        moviecast = context["moviecasts"]
        regionreleasedates = context["regionreleasedates"]

        # Manually check validity of each form in the formset.
        if not all(movierole_form.is_valid() for movierole_form in movierole):
            return self.form_invalid(form)

        if not all(moviecast_form.is_valid() for moviecast_form in moviecast):
            return self.form_invalid(form)

        if not all(
            region_release_date_form.is_valid()
            for region_release_date_form in regionreleasedates
        ):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if movierole.is_valid():
                movierole.instance = self.object
                movierole.save()
            if moviecast.is_valid():
                moviecast.instance = self.object
                moviecast.save()
            if regionreleasedates.is_valid():
                regionreleasedates.instance = self.object
                regionreleasedates.save()
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class MovieDetailView(DetailView):
    model = Movie
    template_name = "watch/movie_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        movie = get_object_or_404(Movie, pk=self.kwargs["pk"])

        content_type = ContentType.objects.get_for_model(Movie)
        content_in_collections = ContentInCollection.objects.filter(
            content_type=content_type, object_id=movie.id
        )
        collections = [
            content_in_collection.collection
            for content_in_collection in content_in_collections
        ]
        context["collections"] = collections

        context["checkin_form"] = WatchCheckInForm(
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": self.request.user.id,
            }
        )

        # Fetch the latest check-in from each user.
        latest_checkin_subquery = WatchCheckIn.objects.filter(
            content_type=content_type.id,
            object_id=self.object.id,
            user=OuterRef("user"),
        ).order_by("-timestamp")
        checkins = (
            WatchCheckIn.objects.filter(
                content_type=content_type.id, object_id=self.object.id
            )
            .annotate(
                latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
            )
            .filter(timestamp=F("latest_checkin"))
        ).order_by("-timestamp")[:5]

        context["checkins"] = checkins

        # Get the count of check-ins for each user for this series
        user_checkin_counts = (
            WatchCheckIn.objects.filter(
                content_type=content_type.id, object_id=self.object.id
            )
            .values("user__username")
            .annotate(total_checkins=Count("id") - 1)
        )

        # Convert to a dictionary for easier lookup
        user_checkin_count_dict = {
            item["user__username"]: item["total_checkins"]
            for item in user_checkin_counts
        }

        # Annotate the checkins queryset with total_checkins for each user
        for checkin in context["checkins"]:
            checkin.total_checkins = user_checkin_count_dict.get(
                checkin.user.username, 0
            )

        # Watch check-in status counts, considering only latest check-in per user
        latest_checkin_status_subquery = (
            WatchCheckIn.objects.filter(
                content_type=content_type.id,
                object_id=self.object.id,
                user=OuterRef("user"),
            )
            .order_by("-timestamp")
            .values("status")[:1]
        )
        latest_checkins = (
            WatchCheckIn.objects.filter(
                content_type=content_type.id, object_id=self.object.id
            )
            .annotate(latest_checkin_status=Subquery(latest_checkin_status_subquery))
            .values("user", "latest_checkin_status")
            .distinct()
        )

        to_watch_count = sum(
            1 for item in latest_checkins if item["latest_checkin_status"] == "to_watch"
        )
        watching_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["watching", "rewatching"]
        )
        watched_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["watched", "rewatched"]
        )

        # Add status counts to context
        context.update(
            {
                "to_watch_count": to_watch_count,
                "watching_count": watching_count,
                "watched_count": watched_count,
                "checkins": checkins,
            }
        )

        context["model_name"] = "movie"

        # Get the ContentType for the Issue model
        movie_content_type = ContentType.objects.get_for_model(Movie)

        # Query ContentInList instances that have the movie as their content_object
        lists_containing_movie = ContentInList.objects.filter(
            content_type=movie_content_type, object_id=self.object.id
        ).order_by("luv_list__title")

        context["lists_containing_movie"] = lists_containing_movie

        roles = {}
        for movie_role in movie.movieroles.all():
            if movie_role.role.name not in roles:
                roles[movie_role.role.name] = []
            d = movie_role.alt_name or movie_role.creator.name
            roles[movie_role.role.name].append((movie_role.creator, d))
        context["roles"] = roles

        # Fetch the latest check-in from the current user for this book
        if self.request.user.is_authenticated:
            latest_user_checkin = (
                WatchCheckIn.objects.filter(
                    content_type=content_type.id,
                    object_id=self.object.id,
                    user=self.request.user,
                )
                .order_by("-timestamp")
                .first()
            )
            if latest_user_checkin is not None:
                context["latest_user_status"] = latest_user_checkin.status
            else:
                context["latest_user_status"] = "to_watch"
        else:
            context["latest_user_status"] = "to_watch"

        context["ordered_release_dates"] = movie.region_release_dates.all().order_by(
            "release_date"
        )

        # contributors
        unique_usernames = {
            record.history_user
            for record in self.object.history.all()
            if record.history_user is not None
        }
        context["contributors"] = unique_usernames

        include_mathjax, include_mermaid = check_required_js(context["checkins"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        content_type = ContentType.objects.get_for_model(Movie)
        form = WatchCheckInForm(
            data=request.POST,
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": request.user.id,
                "comments_enabled": True,
            },
        )
        if form.is_valid():
            movie_check_in = form.save(commit=False)
            movie_check_in.user = request.user  # Set the user manually here
            movie_check_in.save()
        else:
            print(form.errors)

        return redirect(self.object.get_absolute_url())


class MovieUpdateView(LoginRequiredMixin, UpdateView):
    model = Movie
    form_class = MovieForm
    template_name = "watch/movie_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("watch:movie_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["movieroles"] = MovieRoleFormSet(
                self.request.POST, instance=self.object
            )
            data["moviecasts"] = MovieCastFormSet(
                self.request.POST, instance=self.object
            )
            data["regionreleasedates"] = MovieReleaseDateFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["movieroles"] = MovieRoleFormSet(instance=self.object)
            data["moviecasts"] = MovieCastFormSet(instance=self.object)
            data["regionreleasedates"] = MovieReleaseDateFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        movierole = context["movieroles"]
        moviecast = context["moviecasts"]
        regionreleasedates = context["regionreleasedates"]

        # Manually check validity of each form in the formset.
        if not all(movierole_form.is_valid() for movierole_form in movierole):
            return self.form_invalid(form)

        if not all(moviecast_form.is_valid() for moviecast_form in moviecast):
            return self.form_invalid(form)

        if not all(
            region_release_date_form.is_valid()
            for region_release_date_form in regionreleasedates
        ):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if movierole.is_valid():
                movierole.instance = self.object
                movierole.save()
            if moviecast.is_valid():
                moviecast.instance = self.object
                moviecast.save()
            if regionreleasedates.is_valid():
                regionreleasedates.instance = self.object
                regionreleasedates.save()
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class MovieCastDetailView(DetailView):
    model = Movie
    context_object_name = "movie"
    template_name = "watch/movie_cast_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context[
            "moviecasts"
        ] = self.object.moviecasts.all()  # Update with your correct related name
        context["moviecrew"] = self.object.movieroles.all()
        # contributors
        unique_usernames = {
            record.history_user
            for record in self.object.history.all()
            if record.history_user is not None
        }
        context["contributors"] = unique_usernames
        return context


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class WatchListView(TemplateView):
    template_name = "watch/watch_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        movie_content_type = ContentType.objects.get_for_model(Movie)
        series_content_type = ContentType.objects.get_for_model(Series)
        recent_date = timezone.now() - timedelta(days=7)  # Set your cutoff here

        trending_movies = (
            Movie.objects.annotate(
                checkins=Count(
                    "watchcheckin",
                    filter=Q(
                        watchcheckin__content_type=movie_content_type,
                        watchcheckin__timestamp__gte=recent_date,
                    ),
                    distinct=True,
                ),
                latest_checkin=Max(
                    "watchcheckin__timestamp",
                    filter=Q(
                        watchcheckin__content_type=movie_content_type,
                        watchcheckin__timestamp__gte=recent_date,
                    ),
                ),
            )
            .exclude(checkins=0)
            .order_by("-latest_checkin")[:12]
        )

        trending_series = (
            Series.objects.annotate(
                checkins=Count(
                    "watchcheckin",
                    filter=Q(
                        watchcheckin__content_type=series_content_type,
                        watchcheckin__timestamp__gte=recent_date,
                    ),
                    distinct=True,
                ),
                latest_checkin=Max(
                    "watchcheckin__timestamp",
                    filter=Q(
                        watchcheckin__content_type=series_content_type,
                        watchcheckin__timestamp__gte=recent_date,
                    ),
                ),
            )
            .exclude(checkins=0)
            .order_by("-latest_checkin")[:12]
        )

        context["movies"] = Movie.objects.all().order_by("-created_at")[:12]
        context["series"] = Series.objects.all().order_by("-created_at")[:12]
        context["trending_movies"] = trending_movies
        context["trending_series"] = trending_series

        # Include genres with at least one movie or series
        context["genres"] = (
            Genre.objects.filter(Q(movies__isnull=False) | Q(series__isnull=False))
            .order_by("name")
            .distinct()
        )

        context["movies_count"] = Movie.objects.count()
        context["series_count"] = Series.objects.count()
        context["episodes_count"] = Episode.objects.count()

        return context


class WatchListAllView(LoginRequiredMixin, TemplateView):
    template_name = "watch/watch_list_all.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["movies"] = Movie.objects.all().order_by("-created_at")
        context["series"] = Series.objects.all().order_by("-created_at")

        # Include genres with at least one movie or series
        context["genres"] = (
            Genre.objects.filter(Q(movies__isnull=False) | Q(series__isnull=False))
            .order_by("name")
            .distinct()
        )

        context["movies_count"] = Movie.objects.count()
        context["series_count"] = Series.objects.count()
        context["episodes_count"] = Episode.objects.count()

        return context


class SeriesCreateView(LoginRequiredMixin, CreateView):
    model = Series
    form_class = SeriesForm
    template_name = "watch/series_create.html"

    def get_success_url(self):
        return reverse_lazy("watch:series_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["seriesroles"] = SeriesRoleFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["seriesroles"] = SeriesRoleFormSet(instance=self.object)

        return data

    def form_valid(self, form):
        context = self.get_context_data()
        seriesrole = context["seriesroles"]

        # Manually check validity of each form in the formset.
        if not all(seriesrole_form.is_valid() for seriesrole_form in seriesrole):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if seriesrole.is_valid():
                seriesrole.instance = self.object
                seriesrole.save()
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class SeriesDetailView(DetailView):
    model = Series
    template_name = "watch/series_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        content_type = ContentType.objects.get_for_model(Series)
        content_in_collections = ContentInCollection.objects.filter(
            content_type=content_type, object_id=self.object.id
        )
        collections = [
            content_in_collection.collection
            for content_in_collection in content_in_collections
        ]
        context["collections"] = collections

        context["checkin_form"] = WatchCheckInForm(
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": self.request.user.id,
            }
        )

        # Fetch the latest check-in from each user.
        latest_checkin_subquery = WatchCheckIn.objects.filter(
            content_type=content_type.id,
            object_id=self.object.id,
            user=OuterRef("user"),
        ).order_by("-timestamp")
        checkins = (
            WatchCheckIn.objects.filter(
                content_type=content_type.id, object_id=self.object.id
            )
            .annotate(
                latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
            )
            .filter(timestamp=F("latest_checkin"))
        ).order_by("-timestamp")[:5]

        context["checkins"] = checkins

        # Get the count of check-ins for each user for this series
        user_checkin_counts = (
            WatchCheckIn.objects.filter(
                content_type=content_type.id, object_id=self.object.id
            )
            .values("user__username")
            .annotate(total_checkins=Count("id") - 1)
        )

        # Convert to a dictionary for easier lookup
        user_checkin_count_dict = {
            item["user__username"]: item["total_checkins"]
            for item in user_checkin_counts
        }

        # Annotate the checkins queryset with total_checkins for each user
        for checkin in context["checkins"]:
            checkin.total_checkins = user_checkin_count_dict.get(
                checkin.user.username, 0
            )

        # Watch check-in status counts, considering only latest check-in per user
        latest_checkin_status_subquery = (
            WatchCheckIn.objects.filter(
                content_type=content_type.id,
                object_id=self.object.id,
                user=OuterRef("user"),
            )
            .order_by("-timestamp")
            .values("status")[:1]
        )
        latest_checkins = (
            WatchCheckIn.objects.filter(
                content_type=content_type.id, object_id=self.object.id
            )
            .annotate(latest_checkin_status=Subquery(latest_checkin_status_subquery))
            .values("user", "latest_checkin_status")
            .distinct()
        )

        to_watch_count = sum(
            1 for item in latest_checkins if item["latest_checkin_status"] == "to_watch"
        )
        watching_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["watching", "rewatching"]
        )
        watched_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["watched", "rewatched"]
        )

        # Add status counts to context
        context.update(
            {
                "to_watch_count": to_watch_count,
                "watching_count": watching_count,
                "watched_count": watched_count,
                "checkins": checkins,
            }
        )

        context["model_name"] = "series"
        series = get_object_or_404(Series, pk=self.kwargs["pk"])
        context["episodes"] = series.episodes.all().order_by("season", "episode")

        # Get the ContentType for the Issue model
        series_content_type = ContentType.objects.get_for_model(Series)

        # Query ContentInList instances that have the series as their content_object
        lists_containing_series = ContentInList.objects.filter(
            content_type=series_content_type, object_id=self.object.id
        ).order_by("luv_list__title")

        context["lists_containing_series"] = lists_containing_series

        # Fetch the latest check-in from the current user for this book
        if self.request.user.is_authenticated:
            latest_user_checkin = (
                WatchCheckIn.objects.filter(
                    content_type=content_type.id,
                    object_id=self.object.id,
                    user=self.request.user,
                )
                .order_by("-timestamp")
                .first()
            )
            if latest_user_checkin is not None:
                context["latest_user_status"] = latest_user_checkin.status
            else:
                context["latest_user_status"] = "to_watch"
        else:
            context["latest_user_status"] = "to_watch"

        # contributors
        unique_usernames = {
            record.history_user
            for record in self.object.history.all()
            if record.history_user is not None
        }
        context["contributors"] = unique_usernames

        include_mathjax, include_mermaid = check_required_js(context["checkins"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        content_type = ContentType.objects.get_for_model(Series)
        form = WatchCheckInForm(
            data=request.POST,
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": request.user.id,
                "comments_enabled": True,
            },
        )
        if form.is_valid():
            series_check_in = form.save(commit=False)
            series_check_in.user = request.user  # Set the user manually here
            series_check_in.save()
        else:
            print(form.errors)

        return redirect(self.object.get_absolute_url())


class SeriesUpdateView(LoginRequiredMixin, UpdateView):
    model = Series
    form_class = SeriesForm
    template_name = "watch/series_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("watch:series_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["seriesroles"] = SeriesRoleFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["seriesroles"] = SeriesRoleFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        seriesrole = context["seriesroles"]

        # Manually check validity of each form in the formset.
        if not all(seriesrole_form.is_valid() for seriesrole_form in seriesrole):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if seriesrole.is_valid():
                seriesrole.instance = self.object
                seriesrole.save()

        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class SeriesCastDetailView(DetailView):
    model = Series
    context_object_name = "series"
    template_name = "watch/series_cast_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Find all episodes of the series
        episodes = Episode.objects.filter(series=self.object)

        # Extract all casts from those episodes
        casts = EpisodeCast.objects.filter(episode__in=episodes).prefetch_related(
            "creator", "role"
        )

        # Prepare data structure for the episode casts
        episodes_cast = defaultdict(list)
        for cast in casts:
            season_str = str(cast.episode.season).zfill(2)
            episode_str = str(cast.episode.episode).zfill(2)
            episode_num = f"S{season_str}E{episode_str}"

            episodes_cast[cast.creator].append(
                {
                    "character_name": cast.character_name,
                    "role": cast.role,
                    "episode_title": cast.episode.title,
                    "episode_id": cast.episode.id,
                    "episode_num": episode_num,
                    "release_date": cast.episode.release_date,
                }
            )

        # Sort episodes for each cast member by release_date
        for creator, roles in episodes_cast.items():
            episodes_cast[creator] = sorted(roles, key=lambda x: x["release_date"])
        # Sort cast by number of episodes they've participated in
        episodes_cast = dict(
            sorted(episodes_cast.items(), key=lambda x: len(x[1]), reverse=True)
        )

        # Extract all crews from those episodes
        crews = EpisodeRole.objects.filter(episode__in=episodes).prefetch_related(
            "creator", "role"
        )

        # Prepare data structure for the episode crews grouped by roles then creators
        episodes_crew_by_role = defaultdict(lambda: defaultdict(list))
        for crew in crews:
            season_str = str(crew.episode.season).zfill(2)
            episode_str = str(crew.episode.episode).zfill(2)
            episode_num = f"S{season_str}E{episode_str}"

            episodes_crew_by_role[crew.role][crew.creator].append(
                {
                    "episode_title": crew.episode.title,
                    "episode_id": crew.episode.id,
                    "episode_num": episode_num,
                    "release_date": crew.episode.release_date,
                }
            )

        # Convert inner defaultdicts to dict and sort episodes by release_date
        for role, crew_info in episodes_crew_by_role.items():
            for creator, episodes in crew_info.items():
                crew_info[creator] = sorted(episodes, key=lambda x: x["release_date"])
            episodes_crew_by_role[role] = dict(
                sorted(crew_info.items(), key=lambda x: len(x[1]), reverse=True)
            )

        context["episodes_crew_by_role"] = dict(episodes_crew_by_role)

        # Group series crew by their roles
        series_crew_grouped = defaultdict(list)
        for seriesrole in self.object.seriesroles.all():
            series_crew_grouped[seriesrole.role].append(seriesrole)

        context["series_crew"] = dict(series_crew_grouped)
        context["episodes_cast"] = dict(episodes_cast)

        # contributors
        unique_usernames = {
            record.history_user
            for record in self.object.history.all()
            if record.history_user is not None
        }
        context["contributors"] = unique_usernames

        return context


class EpisodeCreateView(LoginRequiredMixin, CreateView):
    model = Episode
    form_class = EpisodeForm
    template_name = "watch/episode_create.html"

    def get_initial(self):
        initial = super().get_initial()
        series_id = self.kwargs.get("series_id")
        initial["series"] = get_object_or_404(Series, pk=series_id)
        return initial

    def get_form(self, form_class=None):
        form = super(EpisodeCreateView, self).get_form(form_class)
        form.fields["series"].disabled = True
        return form

    def get_success_url(self):
        series_id = self.kwargs.get("series_id")
        return reverse("watch:series_detail", kwargs={"pk": series_id})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["episoderoles"] = EpisodeRoleFormSet(
                self.request.POST, instance=self.object
            )
            data["episodecasts"] = EpisodeCastFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["episoderoles"] = EpisodeRoleFormSet(instance=self.object)
            data["episodecasts"] = EpisodeCastFormSet(instance=self.object)

        return data

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        context = self.get_context_data()
        episoderoles = context["episoderoles"]
        episodecasts = context["episodecasts"]

        # Manually check validity of each form in the formset.
        if not all(episoderole_form.is_valid() for episoderole_form in episoderoles):
            return self.form_invalid(form)

        if not all(episodecast_form.is_valid() for episodecast_form in episodecasts):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if episoderoles.is_valid():
                episoderoles.instance = self.object
                episoderoles.save()
            else:
                print(episoderoles.errors)  # print out formset errors
            if episodecasts.is_valid():
                episodecasts.instance = self.object
                episodecasts.save()
            else:
                print(episodecasts.errors)  # print out formset errors
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class EpisodeDetailView(DetailView):
    model = Episode
    template_name = "watch/episode_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        episode = get_object_or_404(Episode, pk=self.kwargs["pk"])
        context["episodecasts"] = episode.episodecasts.all()
        # Group episoderoles by their roles
        episoderoles_grouped = defaultdict(list)
        for episoderole in episode.episoderoles.all():
            episoderoles_grouped[episoderole.role].append(episoderole)

        context["episoderoles"] = dict(episoderoles_grouped)

        # contributors
        unique_usernames = {
            record.history_user
            for record in self.object.history.all()
            if record.history_user is not None
        }
        context["contributors"] = unique_usernames
        return context


class EpisodeUpdateView(LoginRequiredMixin, UpdateView):
    model = Episode
    form_class = EpisodeForm
    template_name = "watch/episode_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        series_id = self.kwargs.get("series_id")
        initial["series"] = get_object_or_404(Series, pk=series_id)
        return initial

    def get_form(self, form_class=None):
        form = super(EpisodeUpdateView, self).get_form(form_class)
        form.fields["series"].disabled = True
        return form

    def get_success_url(self):
        return reverse_lazy(
            "watch:episode_detail",
            kwargs={"pk": self.object.pk, "series_id": self.object.series.pk},
        )

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["episoderoles"] = EpisodeRoleFormSet(
                self.request.POST, instance=self.object
            )
            data["episodecasts"] = EpisodeCastFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["episoderoles"] = EpisodeRoleFormSet(instance=self.object)
            data["episodecasts"] = EpisodeCastFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        episoderoles = context["episoderoles"]
        episodecasts = context["episodecasts"]

        # Manually check validity of each form in the formset.
        if not all(episoderole_form.is_valid() for episoderole_form in episoderoles):
            return self.form_invalid(form)

        if not all(episodecast_form.is_valid() for episodecast_form in episodecasts):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if episoderoles.is_valid():
                episoderoles.instance = self.object
                episoderoles.save()
            if episodecasts.is_valid():
                episodecasts.instance = self.object
                episodecasts.save()
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class EpisodeCastDetailView(DetailView):
    model = Episode
    context_object_name = "episode"
    template_name = "watch/episode_cast_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context[
            "episodecasts"
        ] = self.object.episodecasts.all()  # Update with your correct related name
        context["episoderoles"] = self.object.episoderoles.all()

        # contributors
        unique_usernames = {
            record.history_user
            for record in self.object.history.all()
            if record.history_user is not None
        }
        context["contributors"] = unique_usernames
        return context


###########
# Checkin #
###########


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class WatchCheckInDetailView(DetailView):
    model = WatchCheckIn
    template_name = "watch/watch_checkin_detail.html"
    context_object_name = "checkin"  # This name will be used in your template

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = Comment.objects.filter(
            content_type=ContentType.objects.get_for_model(self.object),
            object_id=self.object.id,
        ).order_by("timestamp")
        context["comment_form"] = CommentForm()
        context["repost_form"] = RepostForm()
        context["app_label"] = self.object._meta.app_label
        context["object_type"] = self.object._meta.model_name.lower()

        checkin_count = WatchCheckIn.objects.filter(
            user=self.object.user,
            content_type=ContentType.objects.get_for_model(self.object.content_object),
            object_id=self.object.content_object.id,
        ).count()
        context["checkin_count"] = checkin_count - 1

        # Determine if the user has upvoted this ReadCheckIn object
        context["has_voted"] = user_has_upvoted(self.request.user, self.object)

        context["is_blocked"] = (
            Block.objects.filter(
                blocker=self.object.user, blocked=self.request.user
            ).exists()
            if self.request.user.is_authenticated
            else False
        )
        include_mathjax, include_mermaid = check_required_js([self.object])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid
        return context


class WatchCheckInUpdateView(LoginRequiredMixin, UpdateView):
    model = WatchCheckIn
    form_class = WatchCheckInForm
    template_name = "watch/watch_checkin_update.html"

    def get_success_url(self):
        return reverse_lazy(
            "write:watch_checkin_detail",
            kwargs={"pk": self.object.pk, "username": self.object.user.username},
        )


class WatchCheckInDeleteView(LoginRequiredMixin, DeleteView):
    model = WatchCheckIn
    template_name = "watch/watch_checkin_delete.html"

    def get_success_url(self):
        if self.object.content_type.model == "movie":
            return reverse_lazy(
                "watch:movie_detail", kwargs={"pk": self.object.content_object.pk}
            )
        else:
            return reverse_lazy(
                "watch:series_detail", kwargs={"pk": self.object.content_object.pk}
            )


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class GenericCheckInListView(ListView):
    model = WatchCheckIn
    template_name = "watch/watch_checkin_list.html"
    context_object_name = "checkins"

    def get_model(self):
        if self.kwargs["model_name"] == "movie":
            return Movie
        elif self.kwargs["model_name"] == "series":
            return Series
        else:
            return None

    def get_queryset(self):
        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        status = self.request.GET.get("status")
        profile_user = get_object_or_404(
            User, username=self.kwargs["username"]
        )  # Get user from url param
        model = self.get_model()
        if model is None:
            checkins = WatchCheckIn.objects.none()
        else:
            content_type = ContentType.objects.get_for_model(model)
            object_id = self.kwargs["object_id"]  # Get object id from url param
            checkins = WatchCheckIn.objects.filter(
                user=profile_user, content_type=content_type, object_id=object_id
            )

        if status:
            if status == "watched_rewatched":
                checkins = checkins.filter(Q(status="watched") | Q(status="rewatched"))
            elif status == "watching_rewatching":
                checkins = checkins.filter(
                    Q(status="watching") | Q(status="rewatching")
                )
            else:
                checkins = checkins.filter(status=status)

        return checkins.order_by(order)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        status = self.request.GET.get("status")  # Added status
        profile_user = get_object_or_404(User, username=self.kwargs["username"])
        context["profile_user"] = profile_user
        context["order"] = order
        context["status"] = status  # Add status to context

        model = self.get_model()
        if model is None:
            context["checkins"] = WatchCheckIn.objects.none()
            context["object"] = None
        else:
            content_type = ContentType.objects.get_for_model(model)
            object_id = self.kwargs["object_id"]  # Get object id from url param
            context[
                "checkins"
            ] = self.get_queryset()  # Use the queryset method to handle status filter

        context["model_name"] = self.kwargs.get("model_name", "movie")

        if self.kwargs["model_name"] == "movie":
            movie = model.objects.get(pk=object_id)
            roles = {}
            for movie_role in movie.movieroles.all():
                if movie_role.role.name not in roles:
                    roles[movie_role.role.name] = []
                d = movie_role.alt_name or movie_role.creator.name
                roles[movie_role.role.name].append((movie_role.creator, d))
            context["roles"] = roles
            context["object"] = movie
        elif self.kwargs["model_name"] == "series":
            series = model.objects.get(pk=object_id)
            roles = {}
            for series_role in series.seriesroles.all():
                if series_role.role.name not in roles:
                    roles[series_role.role.name] = []
                d = series_role.alt_name or series_role.creator.name
                roles[series_role.role.name].append((series_role.creator, d))
            context["roles"] = roles
            context["object"] = series

        include_mathjax, include_mermaid = check_required_js(context["checkins"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        return context


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class GenericCheckInAllListView(ListView):
    model = WatchCheckIn
    template_name = "watch/watch_checkin_list_all.html"
    context_object_name = "checkins"
    paginate_by = 25

    def get_model(self):
        if self.kwargs["model_name"] == "movie":
            return Movie
        elif self.kwargs["model_name"] == "series":
            return Series
        else:
            return None

    def get_queryset(self):
        model = self.get_model()
        if model is None:
            return WatchCheckIn.objects.none()

        content_type = ContentType.objects.get_for_model(model)
        object_id = self.kwargs["object_id"]  # Get object id from url param

        latest_checkin_subquery = WatchCheckIn.objects.filter(
            content_type=content_type, object_id=object_id, user=OuterRef("user")
        ).order_by("-timestamp")

        checkins = (
            WatchCheckIn.objects.filter(content_type=content_type, object_id=object_id)
            .annotate(
                latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
            )
            .filter(timestamp=F("latest_checkin"))
        )

        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        if order == "timestamp":
            checkins = checkins.order_by("timestamp")
        else:
            checkins = checkins.order_by("-timestamp")

        status = self.request.GET.get("status")
        if status:
            if status == "watched_rewatched":
                checkins = checkins.filter(Q(status="watched") | Q(status="rewatched"))
            elif status == "watching_rewatching":
                checkins = checkins.filter(
                    Q(status="watching") | Q(status="rewatching")
                )
            else:
                checkins = checkins.filter(status=status)

        # Adding count of check-ins for each movie or series
        user_checkin_counts = (
            WatchCheckIn.objects.filter(content_type=content_type, object_id=object_id)
            .values("user__username")
            .annotate(total_checkins=Count("id") - 1)
        )

        # Convert to a dictionary for easier lookup
        user_checkin_count_dict = {
            item["user__username"]: item["total_checkins"]
            for item in user_checkin_counts
        }

        # Annotate the checkins queryset with total_checkins for each user
        for checkin in checkins:
            checkin.total_checkins = user_checkin_count_dict.get(
                checkin.user.username, 0
            )

        return checkins

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        model = self.get_model()
        if model is not None:
            context["object"] = model.objects.get(
                pk=self.kwargs["object_id"]
            )  # Get the object details

        context["order"] = self.request.GET.get(
            "order", "-timestamp"
        )  # Default is '-timestamp'

        context["status"] = self.request.GET.get("status", "")
        context["model_name"] = self.kwargs.get("model_name", "movie")

        if context["model_name"] == "movie":
            movie = model.objects.get(pk=self.kwargs["object_id"])
            roles = {}
            for movie_role in movie.movieroles.all():
                if movie_role.role.name not in roles:
                    roles[movie_role.role.name] = []
                d = movie_role.alt_name or movie_role.creator.name
                roles[movie_role.role.name].append((movie_role.creator, d))

        elif context["model_name"] == "series":
            series = model.objects.get(pk=self.kwargs["object_id"])
            roles = {}
            for series_role in series.seriesroles.all():
                if series_role.role.name not in roles:
                    roles[series_role.role.name] = []
                d = series_role.alt_name or series_role.creator.name
                roles[series_role.role.name].append((series_role.creator, d))
        context["roles"] = roles

        include_mathjax, include_mermaid = check_required_js(context["page_obj"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid
        return context


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class GenericCheckInUserListView(ListView):
    """
    All latest check-ins from a given user of all movies and series.
    """

    model = WatchCheckIn
    template_name = "watch/watch_checkin_list_user.html"
    context_object_name = "checkins"
    paginate_by = 25

    def get_queryset(self):
        profile_user = get_object_or_404(User, username=self.kwargs["username"])

        latest_checkin_subquery = WatchCheckIn.objects.filter(
            user=profile_user,
            content_type=OuterRef("content_type"),
            object_id=OuterRef("object_id"),
        ).order_by("-timestamp")

        checkins = (
            WatchCheckIn.objects.filter(user=profile_user)
            .annotate(
                latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
            )
            .filter(timestamp=F("latest_checkin"))
        )

        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        if order == "timestamp":
            checkins = checkins.order_by("timestamp")
        else:
            checkins = checkins.order_by("-timestamp")

        status = self.request.GET.get("status")
        if status:
            if status == "watched_rewatched":
                checkins = checkins.filter(Q(status="watched") | Q(status="rewatched"))
            elif status == "watching_rewatching":
                checkins = checkins.filter(
                    Q(status="watching") | Q(status="rewatching")
                )
            else:
                checkins = checkins.filter(status=status)

        return checkins

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        profile_user = get_object_or_404(User, username=self.kwargs["username"])
        context["profile_user"] = profile_user

        context["order"] = self.request.GET.get(
            "order", "-timestamp"
        )  # Default is '-timestamp'

        context["status"] = self.request.GET.get("status", "")

        include_mathjax, include_mermaid = check_required_js(context["page_obj"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        return context


#########
# Genre #
#########
@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class GenreDetailView(DetailView):
    model = Genre
    template_name = "watch/genre_detail.html"  # Update with your actual template name
    slug_field = "name"
    slug_url_kwarg = "name"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the genre object
        genre = self.object

        # Get all movies and series associated with this genre
        # and order them by release date
        context["movies"] = (
            Movie.objects.filter(genres=genre)
            .annotate(earliest_release_date=Min("region_release_dates__release_date"))
            .order_by("earliest_release_date")
        )
        context["series"] = Series.objects.filter(genres=genre).order_by(
            "-release_date"
        )

        return context


class GenreAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Genre.objects.none()

        qs = Genre.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs.order_by("name")


##############
# Collection #
##############


class CollectionCreateView(LoginRequiredMixin, CreateView):
    model = Collection
    form_class = CollectionForm
    template_name = "watch/collection_create.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["contents"] = ContentInCollectionFormSet(self.request.POST)
        else:
            data["contents"] = ContentInCollectionFormSet(
                queryset=ContentInCollection.objects.none()
            )
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        contents = context["contents"]

        with transaction.atomic():
            form.instance.created_by = self.request.user
            self.object = form.save(commit=False)
            self.object.save()

            if contents.is_valid():
                contents.instance = self.object
                contents.save()
            else:
                return self.form_invalid(form)

        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class CollectionDetailView(DetailView):
    model = Collection
    template_name = "watch/collection_detail.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # contributors
        unique_usernames = {
            record.history_user
            for record in self.object.history.all()
            if record.history_user is not None
        }
        context["contributors"] = unique_usernames
        return context


class CollectionUpdateView(LoginRequiredMixin, UpdateView):
    model = Collection
    form_class = CollectionForm
    template_name = "watch/collection_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["contents"] = ContentInCollectionFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["contents"] = ContentInCollectionFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        contents = context["contents"]

        with transaction.atomic():
            self.object = form.save()

            if contents.is_valid():
                contents.instance = self.object
                contents.save()
            else:
                return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("watch:collection_detail", kwargs={"pk": self.object.pk})


#################
# History Views #
#################


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class MovieHistoryView(HistoryViewMixin, DetailView):
    model = Movie
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class SeriesHistoryView(HistoryViewMixin, DetailView):
    model = Series
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class EpisodeHistoryView(HistoryViewMixin, DetailView):
    model = Episode
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class CollectionHistoryView(HistoryViewMixin, DetailView):
    model = Collection
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context
