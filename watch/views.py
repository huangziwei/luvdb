import re
from collections import defaultdict
from datetime import timedelta
from typing import Any

from dal import autocomplete
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count, F, Max, Min, OuterRef, Q, Subquery
from django.forms.models import inlineformset_factory
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
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
from discover.utils import user_has_upvoted
from entity.forms import CoverImageFormSet
from entity.models import CoverAlbum, CoverImage
from entity.views import HistoryViewMixin, get_contributors
from visit.models import Location
from visit.utils import get_locations_with_parents, get_parent_locations
from write.forms import CommentForm, RepostForm
from write.models import ContentInList
from write.utils import get_visible_checkins, get_visible_comments
from write.utils_bluesky import create_bluesky_post
from write.utils_formatting import check_required_js
from write.utils_mastodon import create_mastodon_post

from .forms import (
    CollectionForm,
    ContentInCollection,
    ContentInCollectionFormSet,
    EpisodeCastForm,
    EpisodeCastFormSet,
    EpisodeForm,
    EpisodeRoleForm,
    EpisodeRoleFormSet,
    MovieCastFormSet,
    MovieForm,
    MovieReleaseDateFormSet,
    MovieRoleFormSet,
    SeasonForm,
    SeasonRole,
    SeasonRoleFormSet,
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
    Season,
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


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
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
                "visibility": "PU",
            }
        )

        # Fetch the latest check-in from each user.
        latest_checkin_subquery = (
            get_visible_checkins(
                self.request.user, WatchCheckIn, content_type, self.object.id
            )
            .filter(user=OuterRef("user"))
            .order_by("-timestamp")
        )
        checkins = (
            get_visible_checkins(
                self.request.user, WatchCheckIn, content_type, self.object.id
            )
            .annotate(
                latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
            )
            .filter(timestamp=F("latest_checkin"))
        ).order_by("-timestamp")[:5]

        context["checkins"] = checkins

        # Get the count of check-ins for each user for this series
        user_checkin_counts = (
            get_visible_checkins(
                self.request.user, WatchCheckIn, content_type, self.object.id
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
            get_visible_checkins(
                self.request.user,
                WatchCheckIn,
                content_type,
                self.object.id,
                checkin_user=OuterRef("user"),
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

        main_role_names = [
            "Director",
            "Screenwriter",
            "Story By",
            "Created By",
        ]
        secondary_role_names = [
            "Exec. Producer",
            "Producer",
            "Editor",
            "Music By",
            "Cinematographer",
        ]

        main_roles = {}
        secondary_roles = {}

        for movie_role in movie.movieroles.all():
            role_name = movie_role.role.name
            alt_name_or_creator_name = movie_role.alt_name or movie_role.creator.name

            if role_name in main_role_names:
                if role_name not in main_roles:
                    main_roles[role_name] = []
                main_roles[role_name].append(
                    (movie_role.creator, alt_name_or_creator_name)
                )
            elif role_name in secondary_role_names:
                if role_name not in secondary_roles:
                    secondary_roles[role_name] = []
                secondary_roles[role_name].append(
                    (movie_role.creator, alt_name_or_creator_name)
                )

        context["main_roles"] = main_roles
        context["secondary_roles"] = secondary_roles

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

        release_dates = movie.region_release_dates.all().order_by("release_date")
        grouped_release_dates = {}
        for release_date in release_dates:
            if release_date.release_type not in grouped_release_dates:
                grouped_release_dates[release_date.release_type] = []
            grouped_release_dates[release_date.release_type].append(release_date)

        context["grouped_release_dates"] = grouped_release_dates

        # contributors
        context["contributors"] = get_contributors(self.object)

        include_mathjax, include_mermaid = check_required_js(context["checkins"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        # related locations
        context["filming_locations_with_parents"] = get_locations_with_parents(
            self.object.filming_locations
        )
        context["setting_locations_with_parents"] = get_locations_with_parents(
            self.object.setting_locations
        )

        context["has_voted"] = user_has_upvoted(self.request.user, self.object)
        context["can_vote"] = (
            self.request.user.is_authenticated
            and WatchCheckIn.objects.filter(
                content_type=ContentType.objects.get_for_model(Movie),
                object_id=self.object.id,
                user=self.request.user,
                status__in=["watched", "rewatched"],
            ).exists()
        )

        context["official_sountracks"] = self.object.soundtracks.all().order_by(
            "release_date"
        )
        context["featured_tracks"] = self.object.tracks.all().order_by("release_date")
        context["opening_theme_songs"] = self.object.theme_songs.all().order_by(
            "release_date"
        )
        context["ending_credit_songs"] = self.object.ending_songs.all().order_by(
            "release_date"
        )

        # mentioned media
        context["mentioned_litworks"] = self.object.mentioned_litworks.all().order_by(
            "publication_date"
        )
        context["mentioned_litinstances"] = (
            self.object.mentioned_litinstances.all().order_by("publication_date")
        )
        context["mentioned_books"] = self.object.mentioned_books.all().order_by(
            "publication_date"
        )
        context["mentioned_gameworks"] = self.object.mentioned_gameworks.all().order_by(
            "first_release_date"
        )
        context["mentioned_games"] = (
            self.object.mentioned_games.all()
            .annotate(release_date=Min("region_release_dates__release_date"))
            .order_by("release_date")
        )
        context["mentioned_movies"] = (
            self.object.mentioned_movies.all()
            .annotate(release_date=Min("region_release_dates__release_date"))
            .order_by("release_date")
        )
        context["mentioned_series"] = self.object.mentioned_series.all().order_by(
            "release_date"
        )
        context["mentioned_musicalworks"] = (
            self.object.mentioned_musicalworks.all().order_by("release_date")
        )

        context["mentioned_tracks"] = self.object.mentioned_tracks.all().order_by(
            "release_date"
        )
        context["mentioned_releases"] = self.object.mentioned_releases.all().order_by(
            "release_date"
        )
        context["mentioned_locations"] = self.object.mentioned_locations.all().order_by(
            "name"
        )

        context["stars"] = movie.moviecasts.filter(is_star=True).order_by("order")

        # additional images
        # Get additional covers (excluding the primary one)
        additional_covers = CoverImage.objects.filter(
            cover_album__content_type=ContentType.objects.get_for_model(Movie),
            cover_album__object_id=movie.id
        ).exclude(image=movie.poster)

        # Combine cover field and additional covers
        all_covers = [{"url": movie.poster.url, "is_primary": True}] if movie.poster else []
        all_covers += [{"url": cover.image.url, "is_primary": False} for cover in additional_covers]

        context["all_covers"] = all_covers

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
        movie = self.object
        # Fetch or create CoverAlbum for this movie
        cover_album, created = CoverAlbum.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Movie), object_id=movie.pk,
        )

        # Exclude primary cover from additional images
        primary_cover_path = movie.poster.name if movie.poster else None
        additional_covers_qs = cover_album.images.exclude(image=primary_cover_path)

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
            data["coverimages"] = CoverImageFormSet(
                self.request.POST, self.request.FILES, instance=cover_album, queryset=additional_covers_qs
            ) 
        else:
            data["movieroles"] = MovieRoleFormSet(instance=self.object)
            data["moviecasts"] = MovieCastFormSet(instance=self.object)
            data["regionreleasedates"] = MovieReleaseDateFormSet(instance=self.object)
            data["coverimages"] = CoverImageFormSet(instance=cover_album, queryset=additional_covers_qs)

        return data

    def form_valid(self, form):
        context = self.get_context_data()
        movierole = context["movieroles"]
        moviecast = context["moviecasts"]
        regionreleasedates = context["regionreleasedates"]
        coverimages = context["coverimages"]

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
            if coverimages.is_valid():
                # ✅ Check each form for deletion
                for cover_form in coverimages.forms:
                    if cover_form.cleaned_data.get("DELETE"):
                        cover_instance = cover_form.instance
                        if cover_instance.image:
                            cover_instance.image.delete(save=False)  # Remove file from storage
                        cover_instance.delete()  # Delete from database

                coverimages.instance = CoverAlbum.objects.get(
                    content_type=ContentType.objects.get_for_model(Movie),
                    object_id=self.object.id
                )
                coverimages.save()
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class MovieCastDetailView(DetailView):
    model = Movie
    context_object_name = "movie"
    template_name = "watch/movie_cast_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["moviecasts"] = (
            self.object.moviecasts.all()
        )  # Update with your correct related name
        context["moviecrew"] = self.object.movieroles.all()
        # contributors
        context["contributors"] = get_contributors(self.object)

        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class WatchListView(TemplateView):
    template_name = "watch/watch_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        movie_content_type = ContentType.objects.get_for_model(Movie)
        series_content_type = ContentType.objects.get_for_model(Series)
        season_content_type = ContentType.objects.get_for_model(Season)
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
        context["seasons"] = Season.objects.all().order_by("-created_at")[:12]
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


class WatchListAllView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "watch/watch_list_all.html"

    def test_func(self):
        # Only allow superusers
        return self.request.user.is_superuser

    def handle_no_permission(self):
        # If not allowed, raise a 404 error
        raise Http404

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
            self.create_season(self.object)

        return super().form_valid(form)

    def create_season(self, series):
        first_season = Season(
            series=series,
            title=f"{series.title} Season 1",
            season_number=1,
            season_label="Season",
            subtitle=series.subtitle,
            other_titles=series.other_titles,
            release_date=series.release_date,
            notes=series.notes,
            website=series.website,
            poster=series.poster,
            poster_sens=series.poster_sens,
            duration=series.duration,
            languages=series.languages,
            status=series.status,
            imdb=series.imdb,
            wikipedia=series.wikipedia,
            official_website=series.official_website,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        first_season.save()

        # Copy ManyToMany fields to the season
        first_season.studios.set(series.studios.all())
        first_season.distributors.set(series.distributors.all())
        first_season.stars.set(series.stars.all())
        first_season.genres.set(series.genres.all())

        # Copy SeriesRole to SeasonRole
        for series_role in series.seriesroles.all():
            SeasonRole.objects.create(
                season=first_season,
                creator=series_role.creator,
                role=series_role.role,
                alt_name=series_role.alt_name,
            )


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class SeriesDetailView(DetailView):
    model = Series
    template_name = "watch/series_detail.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        seasons = self.object.seasons.all()

        # Check if 'force_detail' is in the query parameters
        force_detail = request.GET.get("detail", "false").lower() == "true"

        # Redirect to the first season if there's only one season and 'force_detail' is not set
        if seasons.count() == 1 and not force_detail:
            season = seasons.first()
            return redirect(
                "watch:season_detail",
                series_id=self.object.id,
                season_number=season.season_number,
            )

        return super().get(request, *args, **kwargs)

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

        context["model_name"] = "series"
        series = get_object_or_404(Series, pk=self.kwargs["pk"])

        context["seasons"] = series.seasons.order_by("release_date")

        # Get the ContentType for the Issue model
        series_content_type = ContentType.objects.get_for_model(Series)

        # Query ContentInList instances that have the series as their content_object
        lists_containing_series = ContentInList.objects.filter(
            content_type=series_content_type, object_id=self.object.id
        ).order_by("luv_list__title")

        context["lists_containing_series"] = lists_containing_series

        # contributors
        context["contributors"] = get_contributors(self.object)

        main_role_names = [
            "Director",
            "Screenwriter",
            "Story By",
            "Created By",
            "Showrunner",
        ]
        secondary_role_names = [
            "Exec. Producer",
            "Producer",
            "Editor",
            "Music By",
            "Cinematographer",
            "Character Designer",
        ]

        main_roles = {}
        secondary_roles = {}

        for series_role in series.seriesroles.all():
            role_name = series_role.role.name
            alt_name_or_creator_name = series_role.alt_name or series_role.creator.name

            if role_name in main_role_names:
                if role_name not in main_roles:
                    main_roles[role_name] = []
                main_roles[role_name].append(
                    (series_role.creator, alt_name_or_creator_name)
                )
            elif role_name in secondary_role_names:
                if role_name not in secondary_roles:
                    secondary_roles[role_name] = []
                secondary_roles[role_name].append(
                    (series_role.creator, alt_name_or_creator_name)
                )

        context["main_roles"] = main_roles
        context["secondary_roles"] = secondary_roles

        return context


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


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class SeriesCastDetailView(DetailView):
    model = Series
    context_object_name = "series"
    template_name = "watch/series_cast_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Find all seasons of the series
        seasons = Season.objects.filter(series=self.object)

        # Prepare to aggregate cast and crew data across all seasons
        episodes_cast = defaultdict(list)
        episodes_crew_by_role = defaultdict(lambda: defaultdict(list))

        # Iterate over each season to gather data
        for season in seasons:
            # Find all episodes of the current season
            episodes = Episode.objects.filter(season=season)

            # Extract all casts from those episodes
            casts = EpisodeCast.objects.filter(episode__in=episodes).prefetch_related(
                "creator", "role"
            )

            # Aggregate cast data
            for cast in casts:
                episode_num = cast.episode.episode
                season_num = cast.episode.season.season_number
                episodes_cast[cast.creator].append(
                    {
                        "character_name": cast.character_name,
                        "role": cast.role,
                        "episode_title": cast.episode.title,
                        "episode_id": cast.episode.id,
                        "episode_num": episode_num,
                        "season_num": season_num,
                        "release_date": cast.episode.release_date,
                    }
                )

            # Extract all crews from those episodes
            crews = EpisodeRole.objects.filter(episode__in=episodes).prefetch_related(
                "creator", "role"
            )

            # Aggregate crew data grouped by roles then creators
            for crew in crews:
                episode_num = crew.episode.episode
                season_num = crew.episode.season.season_number

                episodes_crew_by_role[crew.role][crew.creator].append(
                    {
                        "episode_title": crew.episode.title,
                        "episode_id": crew.episode.id,
                        "episode_num": episode_num,
                        "season_num": season_num,
                        "release_date": crew.episode.release_date,
                    }
                )

        # Sort episodes for each cast member by release_date
        for creator, roles in episodes_cast.items():
            episodes_cast[creator] = sorted(roles, key=lambda x: x["release_date"])

        # Sort cast by number of episodes they've participated in
        episodes_cast = dict(
            sorted(episodes_cast.items(), key=lambda x: len(x[1]), reverse=True)
        )

        # Sort and finalize crew data
        for role, crew_info in episodes_crew_by_role.items():
            for creator, episodes in crew_info.items():
                crew_info[creator] = sorted(episodes, key=lambda x: x["release_date"])
            episodes_crew_by_role[role] = dict(
                sorted(crew_info.items(), key=lambda x: len(x[1]), reverse=True)
            )

        context["episodes_cast"] = dict(episodes_cast)
        context["episodes_crew_by_role"] = dict(episodes_crew_by_role)

        # Group series crew by their roles (from series itself)
        series_crew_grouped = defaultdict(list)
        for seriesrole in self.object.seriesroles.all():
            series_crew_grouped[seriesrole.role].append(seriesrole)

        context["series_crew"] = dict(series_crew_grouped)

        # contributors
        context["contributors"] = get_contributors(self.object)

        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class SeasonCastDetailView(DetailView):
    model = Season
    context_object_name = "season"
    template_name = "watch/season_cast_detail.html"

    def get_object(self):
        series_id = self.kwargs.get("series_id")
        season_number = self.kwargs.get("season_number")
        return get_object_or_404(
            Season, series_id=series_id, season_number=season_number
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Find all episodes of the season
        episodes = Episode.objects.filter(season=self.object)

        # Extract all casts from those episodes
        casts = EpisodeCast.objects.filter(episode__in=episodes).prefetch_related(
            "creator", "role"
        )

        # Prepare data structure for the episode casts
        episodes_cast = defaultdict(list)
        for cast in casts:
            episode_num = cast.episode.episode

            episodes_cast[cast.creator].append(
                {
                    "alt_name": cast.alt_name,
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
            episode_num = crew.episode.episode

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
        for seasonrol in self.object.seasonroles.all():
            series_crew_grouped[seasonrol.role].append(seasonrol)

        context["series_crew"] = dict(series_crew_grouped)
        context["episodes_cast"] = dict(episodes_cast)

        # contributors
        context["contributors"] = get_contributors(self.object)

        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class SeasonDetailView(DetailView):
    model = Season
    template_name = "watch/season_detail.html"

    def get_object(self):
        series_id = self.kwargs.get("series_id")
        season_number = self.kwargs.get("season_number")
        return get_object_or_404(
            Season, series_id=series_id, season_number=season_number
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        content_type = ContentType.objects.get_for_model(Season)
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
                "visibility": "PU",
            }
        )

        # Fetch the latest check-in from each user.
        latest_checkin_subquery = (
            get_visible_checkins(
                self.request.user,
                WatchCheckIn,
                content_type,
                self.object.id,
            )
            .filter(user=OuterRef("user"))
            .order_by("-timestamp")
        )
        checkins = (
            get_visible_checkins(
                self.request.user,
                WatchCheckIn,
                content_type,
                self.object.id,
            )
            .annotate(
                latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
            )
            .filter(timestamp=F("latest_checkin"))
        ).order_by("-timestamp")[:5]

        context["checkins"] = checkins

        # Get the count of check-ins for each user for this series
        user_checkin_counts = (
            get_visible_checkins(
                self.request.user,
                WatchCheckIn,
                content_type,
                self.object.id,
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
            get_visible_checkins(
                self.request.user,
                WatchCheckIn,
                content_type,
                self.object.id,
                checkin_user=OuterRef("user"),
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

        context["model_name"] = "season"
        season = get_object_or_404(
            Season,
            series_id=self.kwargs["series_id"],
            season_number=self.kwargs["season_number"],
        )

        episodes = season.episodes.all().order_by("episode")
        context["episodes"] = episodes

        # Get the ContentType for the Issue model
        season_content_type = ContentType.objects.get_for_model(Season)
        # Query ContentInList instances that have the series as their content_object
        lists_containing_season = ContentInList.objects.filter(
            content_type=season_content_type, object_id=self.object.id
        ).order_by("luv_list__title")

        context["lists_containing_season"] = lists_containing_season

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
        context["contributors"] = get_contributors(self.object)

        include_mathjax, include_mermaid = check_required_js(context["checkins"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        unique_filming_locations_with_parents_set = set()
        unique_setting_locations_with_parents_set = set()
        # for episode in season.episodes.all().order_by("season", "episode"):
        #     filming_locations_with_parents = get_locations_with_parents(
        #         episode.filming_locations
        #     )
        #     setting_locations_with_parents = get_locations_with_parents(
        #         episode.setting_locations
        #     )

        #     # Process each location with its parents
        #     for location, parents in filming_locations_with_parents:
        #         # Convert location and its parents to their unique identifiers
        #         location_id = location.pk  # Assuming pk is the primary key
        #         parent_ids = tuple(parent.pk for parent in parents)

        #         # Add the tuple of identifiers to the set
        #         unique_filming_locations_with_parents_set.add((location_id, parent_ids))

        #     for location, parents in setting_locations_with_parents:
        #         # Convert location and its parents to their unique identifiers
        #         location_id = location.pk  # Assuming pk is the primary key
        #         parent_ids = tuple(parent.pk for parent in parents)

        #         # Add the tuple of identifiers to the set
        #         unique_setting_locations_with_parents_set.add((location_id, parent_ids))

        # Convert back to the original Location objects
        context["filming_locations_with_parents"] = [
            (
                Location.objects.get(pk=location_id),
                [Location.objects.get(pk=parent_id) for parent_id in parent_ids],
            )
            for location_id, parent_ids in unique_filming_locations_with_parents_set
        ]
        context["setting_locations_with_parents"] = [
            (
                Location.objects.get(pk=location_id),
                [Location.objects.get(pk=parent_id) for parent_id in parent_ids],
            )
            for location_id, parent_ids in unique_setting_locations_with_parents_set
        ]

        main_role_names = [
            "Director",
            "Screenwriter",
            "Story By",
            "Created By",
            "Showrunner",
        ]
        secondary_role_names = [
            "Exec. Producer",
            "Producer",
            "Editor",
            "Music By",
            "Cinematographer",
            "Character Designer",
        ]

        main_roles = {}
        secondary_roles = {}

        for season_role in season.seasonroles.all():
            role_name = season_role.role.name
            alt_name_or_creator_name = season_role.alt_name or season_role.creator.name

            if role_name in main_role_names:
                if role_name not in main_roles:
                    main_roles[role_name] = []
                main_roles[role_name].append(
                    (season_role.creator, alt_name_or_creator_name)
                )
            elif role_name in secondary_role_names:
                if role_name not in secondary_roles:
                    secondary_roles[role_name] = []
                secondary_roles[role_name].append(
                    (season_role.creator, alt_name_or_creator_name)
                )

        context["main_roles"] = main_roles
        context["secondary_roles"] = secondary_roles

        context["has_voted"] = user_has_upvoted(self.request.user, self.object)
        context["can_vote"] = (
            self.request.user.is_authenticated
            and WatchCheckIn.objects.filter(
                content_type=ContentType.objects.get_for_model(Series),
                object_id=self.object.id,
                user=self.request.user,
                status__in=["watched", "rewatched"],
            ).exists()
        )

        context["seasons"] = Season.objects.filter(series=self.object.series).order_by(
            "season_number"
        )

        # additional images
        # Get additional covers (excluding the primary one)
        additional_covers = CoverImage.objects.filter(
            cover_album__content_type=ContentType.objects.get_for_model(Season),
            cover_album__object_id=season.id
        ).exclude(image=season.poster)

        # Combine cover field and additional covers
        all_covers = [{"url": season.poster.url, "is_primary": True}] if season.poster else []
        all_covers += [{"url": cover.image.url, "is_primary": False} for cover in additional_covers]

        context["all_covers"] = all_covers

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


class SeasonUpdateView(LoginRequiredMixin, UpdateView):
    model = Season
    form_class = SeasonForm
    template_name = "watch/season_update.html"

    def get_object(self, queryset=None):
        series_id = self.kwargs.get("series_id")
        season_number = self.kwargs.get("season_number")
        return get_object_or_404(
            Season, series__id=series_id, season_number=season_number
        )

    def get_success_url(self):
        return reverse_lazy(
            "watch:season_detail",
            kwargs={
                "series_id": self.object.series.id,
                "season_number": self.object.season_number,
            },
        )

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        season = self.object
        # Fetch or create CoverAlbum for this season
        cover_album, created = CoverAlbum.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Season), object_id=season.pk,
        )

        # Exclude primary cover from additional images
        primary_cover_path = season.poster.name if season.poster else None
        additional_covers_qs = cover_album.images.exclude(image=primary_cover_path)

        if self.request.POST:
            data["seasonroles"] = SeasonRoleFormSet(
                self.request.POST, instance=self.object
            )
            data["coverimages"] = CoverImageFormSet(
                self.request.POST, self.request.FILES, instance=cover_album, queryset=additional_covers_qs
            ) 
        else:
            data["seasonroles"] = SeasonRoleFormSet(instance=self.object)
            data["coverimages"] = CoverImageFormSet(instance=cover_album, queryset=additional_covers_qs)

        return data

    def form_valid(self, form):
        context = self.get_context_data()
        seasonrole = context["seasonroles"]
        coverimages = context["coverimages"]

        # Manually check validity of each form in the formset.
        if not all(seasonrole_form.is_valid() for seasonrole_form in seasonrole):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if seasonrole.is_valid():
                seasonrole.instance = self.object
                seasonrole.save()
            if coverimages.is_valid():
                # ✅ Check each form for deletion
                for cover_form in coverimages.forms:
                    if cover_form.cleaned_data.get("DELETE"):
                        cover_instance = cover_form.instance
                        if cover_instance.image:
                            cover_instance.image.delete(save=False)  # Remove file from storage
                        cover_instance.delete()  # Delete from database

                coverimages.instance = CoverAlbum.objects.get(
                    content_type=ContentType.objects.get_for_model(Season),
                    object_id=self.object.id
                )
                coverimages.save()

        return super().form_valid(form)


class SeasonCreateView(LoginRequiredMixin, CreateView):
    model = Season
    form_class = SeasonForm
    template_name = "watch/season_create.html"

    def get_success_url(self):
        return reverse_lazy(
            "watch:season_detail",
            kwargs={
                "series_id": self.object.series.id,
                "season_number": self.object.season_number,
            },
        )

    def get_initial(self):
        initial = super().get_initial()
        series_id = self.kwargs.get("series_id")
        season_number = self.kwargs.get("season_number")

        origin_season = get_object_or_404(
            Season, series_id=series_id, season_number=season_number
        )

        initial.update(
            {
                "series": origin_season.series,
                "title": f"{origin_season.series.title} Season {origin_season.season_number + 1}",
                "season_number": origin_season.season_number + 1,
                "season_label": origin_season.season_label,
                "subtitle": origin_season.subtitle,
                "other_titles": origin_season.other_titles,
                "release_date": origin_season.release_date,
                "notes": origin_season.notes,
                "website": origin_season.website,
                "poster": origin_season.poster,
                "poster_sens": origin_season.poster_sens,
                "duration": origin_season.duration,
                "languages": origin_season.languages,
                "status": origin_season.status,
                "imdb": origin_season.imdb,
                "wikipedia": origin_season.wikipedia,
                "official_website": origin_season.official_website,
            }
        )

        self.origin_season = origin_season

        return initial

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        series_id = self.kwargs.get("series_id")
        season_number = self.kwargs.get("season_number")
        origin_season = get_object_or_404(
            Season, series_id=series_id, season_number=season_number
        )

        if self.request.POST:
            data["seasonroles"] = SeasonRoleFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["seasonroles"] = SeasonRoleFormSet(instance=self.object)
            initial_roles = [
                {
                    "creator": role.creator.id,
                    "role": role.role.id,
                    "alt_name": role.alt_name,
                }
                for role in origin_season.seasonroles.all()
            ]

            SeasonRoleFormSet_prefilled = inlineformset_factory(
                Season,
                SeasonRole,
                form=SeasonRoleFormSet.form,
                extra=len(initial_roles),
                can_delete=True,
            )
            data["seasonroles"] = SeasonRoleFormSet_prefilled(
                instance=self.object, initial=initial_roles
            )

            # Prefill the form with M2M data from the original season
            data["form"].fields["studios"].initial = origin_season.studios.all()
            data["form"].fields[
                "distributors"
            ].initial = origin_season.distributors.all()
            data["form"].fields["stars"].initial = origin_season.stars.all()
            data["form"].fields["genres"].initial = origin_season.genres.all()
            data["form"].fields[
                "based_on_litworks"
            ].initial = origin_season.based_on_litworks.all()
            data["form"].fields[
                "based_on_games"
            ].initial = origin_season.based_on_games.all()
            data["form"].fields[
                "based_on_series"
            ].initial = origin_season.based_on_series.all()
            data["form"].fields[
                "based_on_movies"
            ].initial = origin_season.based_on_movies.all()
            data["form"].fields["soundtracks"].initial = origin_season.soundtracks.all()

        return data

    def form_valid(self, form):
        context = self.get_context_data()
        seasonroles = context["seasonroles"]

        with transaction.atomic():
            self.object = form.save()

            if seasonroles.is_valid():
                seasonroles.instance = self.object
                seasonroles.save()

        return super().form_valid(form)


class EpisodeCreateView(LoginRequiredMixin, CreateView):
    model = Episode
    form_class = EpisodeForm
    template_name = "watch/episode_create.html"

    def get_initial(self):
        initial = super().get_initial()
        series_id = self.kwargs.get("series_id")
        season_number = self.kwargs.get("season_number")
        initial["season"] = get_object_or_404(
            Season, series_id=series_id, season_number=season_number
        )
        initial["series"] = initial["season"].series

        origin_episode_id = self.kwargs.get("origin_episode_id", None)
        if origin_episode_id:
            origin_episode = get_object_or_404(Episode, id=origin_episode_id)

            initial.update(
                {
                    "title": origin_episode.title,
                    "subtitle": origin_episode.subtitle,
                    "episode": origin_episode.episode + 1,
                    "wikipedia": origin_episode.wikipedia,
                    "imdb": origin_episode.imdb,
                }
            )

        return initial

    def get_form(self, form_class=None):
        form = super(EpisodeCreateView, self).get_form(form_class)
        form.fields["season"].disabled = True
        form.fields["series"].disabled = True
        return form

    def get_success_url(self):
        series_id = self.kwargs.get("series_id")
        return reverse(
            "watch:episode_detail",
            kwargs={
                "series_id": series_id,
                "season_number": self.object.season.season_number,
                "episode_number": self.object.episode,
            },
        )

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        origin_episode_id = self.kwargs.get("origin_episode_id", None)

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

            if origin_episode_id:
                origin_episode = get_object_or_404(Episode, id=origin_episode_id)
                episode_roles = origin_episode.episoderoles.all()
                episode_casts = origin_episode.episodecasts.all()

                initial_roles = [
                    {
                        "creator": role.creator.id,
                        "role": role.role.id,
                        "alt_name": role.alt_name,
                    }
                    for role in episode_roles
                ]

                EpisodeRoleFormSet_prefilled = inlineformset_factory(
                    Episode,
                    EpisodeRole,
                    form=EpisodeRoleForm,
                    extra=1 if len(initial_roles) == 0 else len(initial_roles),
                    can_delete=True,
                    widgets={
                        "creator": autocomplete.ModelSelect2(
                            url=reverse_lazy("entity:creator-autocomplete"),
                            attrs={
                                "data-create-url": reverse_lazy("entity:creator_create")
                            },
                        ),
                        "role": autocomplete.ModelSelect2(
                            url=reverse_lazy("entity:role-autocomplete"),
                            forward=["domain"],
                            attrs={
                                "data-create-url": reverse_lazy("entity:role_create")
                            },
                        ),
                    },
                    help_texts={
                        "creator": "<a href='/entity/creator/create/'>Add a new creator</a>.",
                        "role": "<a href='/entity/role/create/'>Add a new role</a>.",
                    },
                )

                initial_casts = [
                    {
                        "creator": role.creator.id,
                        "role": role.role.id,
                        "character_name": role.character_name,
                    }
                    for role in episode_casts
                ]

                EpisodeCastFormSet_prefilled = inlineformset_factory(
                    Episode,
                    EpisodeCast,
                    form=EpisodeCastForm,
                    extra=1 if len(initial_casts) == 0 else len(initial_casts),
                    can_delete=True,
                    widgets={
                        "creator": autocomplete.ModelSelect2(
                            url=reverse_lazy("entity:creator-autocomplete"),
                            attrs={
                                "data-create-url": reverse_lazy("entity:creator_create")
                            },
                        ),
                        "role": autocomplete.ModelSelect2(
                            url=reverse_lazy("entity:role-autocomplete"),
                            forward=["domain"],
                            attrs={
                                "data-create-url": reverse_lazy("entity:role_create")
                            },
                        ),
                    },
                    help_texts={
                        "creator": "<a href='/entity/creator/create/'>Add a new creator</a>.",
                        "role": "<a href='/entity/role/create/'>Add a new role</a>.",
                    },
                )

                data["episoderoles"] = EpisodeRoleFormSet_prefilled(
                    instance=self.object, initial=initial_roles
                )
                data["episodecasts"] = EpisodeCastFormSet_prefilled(
                    instance=self.object, initial=initial_casts
                )

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


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class EpisodeDetailView(DetailView):
    model = Episode
    template_name = "watch/episode_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        episode = self.get_object()
        context["episodecasts"] = episode.episodecasts.all()
        # Group episoderoles by their roles
        episoderoles_grouped = defaultdict(list)
        for episoderole in episode.episoderoles.all():
            episoderoles_grouped[episoderole.role].append(episoderole)

        context["episoderoles"] = dict(episoderoles_grouped)

        # contributors
        context["contributors"] = get_contributors(self.object)

        series_id = episode.series.id
        # Add check-ins related to the current episode
        # Modify the check-ins query for season 1 episodes
        season_episode_format = (
            f"S{episode.season.season_number:02d}E{episode.episode:02d}"
        )
        if episode.season == 1:
            season_episode_short_format = f"E{episode.episode:02d}"
            progress_formats = [season_episode_format, season_episode_short_format]
        else:
            progress_formats = [season_episode_format]

        # Filter WatchCheckIn instances
        check_ins = WatchCheckIn.objects.filter(
            Q(object_id=series_id) & Q(progress__in=progress_formats)
        )
        context["episode_checkins"] = check_ins
        episodes = episode.season.episodes.all().order_by("episode")
        context["episodes"] = episodes
        seasons = defaultdict(list)
        for episode in episodes:
            seasons[episode.season].append(episode)
        context["seasons"] = dict(seasons)

        context["filming_locations_with_parents"] = get_locations_with_parents(
            episode.filming_locations
        )
        context["setting_locations_with_parents"] = get_locations_with_parents(
            episode.setting_locations
        )
        return context

    def get_object(self):
        # Get the series_id and season_episode string from the URL parameters
        series_id = self.kwargs.get("series_id")
        season_number = self.kwargs.get("season_number")
        season_id = get_object_or_404(
            Season, series_id=series_id, season_number=season_number
        ).id
        episode_number = self.kwargs.get("episode_number")

        # Fetch the Episode object based on series_id, season, and episode
        return get_object_or_404(
            Episode,
            series_id=series_id,
            season_id=season_id,
            episode=episode_number,
        )


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
        form.fields["season"].disabled = True
        return form

    def get_success_url(self):
        return reverse_lazy(
            "watch:episode_detail",
            kwargs={
                "season_number": self.object.season.season_number,
                "episode_number": self.object.episode,
                "series_id": self.object.series.pk,
            },
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

    def get_object(self):
        # Get the series_id and season_episode string from the URL parameters
        series_id = self.kwargs.get("series_id")
        season_number = self.kwargs.get("season_number")
        season_id = get_object_or_404(
            Season, series_id=series_id, season_number=season_number
        ).id
        episode_number = self.kwargs.get("episode_number")

        # Fetch the Episode object based on series_id, season, and episode
        return get_object_or_404(
            Episode,
            series_id=series_id,
            season_id=season_id,
            episode=episode_number,
        )


###########
# Checkin #
###########


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class WatchCheckInDetailView(DetailView):
    model = WatchCheckIn
    template_name = "watch/watch_checkin_detail.html"
    context_object_name = "checkin"  # This name will be used in your template

    def dispatch(self, request, *args, **kwargs):
        user = self.get_object().user  # Assume `Say` has a ForeignKey to `CustomUser`

        # Check privacy settings
        if user.privacy_level == "logged_in_only" and not request.user.is_authenticated:
            # If privacy level is 'logged_in_only' and user is not authenticated, redirect to login
            return redirect("{}?next={}".format(reverse("login"), request.path))
        # No restriction for 'limited' since detail views should be accessible to non-logged-in users

        # Otherwise, proceed as normal
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.visibility != "PU" and self.request.user not in obj.visible_to.all():
            raise Http404("You do not have permission to view this.")
        return obj

    def get(self, request, *args, **kwargs):
        if not request.GET.get("reply") and not request.GET.get("repost"):
            return HttpResponseRedirect(f"{request.path}?reply=true")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        checkin = self.get_object()
        if "crosspost_mastodon" in request.POST and hasattr(
            request.user, "mastodon_account"
        ):
            url = request.build_absolute_uri(checkin.get_absolute_url())
            create_mastodon_post(
                handle=request.user.mastodon_account.mastodon_handle,
                access_token=request.user.mastodon_account.get_mastodon_access_token(),
                text=checkin.content,
                url=url,
            )
        elif "crosspost_bluesky" in request.POST and hasattr(
            request.user, "bluesky_account"
        ):
            url = request.build_absolute_uri(checkin.get_absolute_url())
            create_bluesky_post(
                handle=request.user.bluesky_account.bluesky_handle,
                pds_url=request.user.bluesky_account.bluesky_pds_url,
                password=request.user.bluesky_account.get_bluesky_app_password(),
                text=checkin.content,
                content_id=checkin.id,
                content_username=request.user.username,
                content_type="WatchCheckIn",
            )
        return HttpResponseRedirect(request.path_info)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = get_visible_comments(self.request.user, self.object)
        context["comment_form"] = CommentForm()
        context["repost_form"] = RepostForm(user=self.request.user)
        context["app_label"] = self.object._meta.app_label
        context["object_type"] = self.object._meta.model_name.lower()

        checkin_count = WatchCheckIn.objects.filter(
            user=self.object.user,
            content_type=ContentType.objects.get_for_model(self.object.content_object),
            object_id=self.object.content_object.id,
        ).count()
        context["checkin_count"] = checkin_count - 1

        # Determine if the user has upvoted this WatchCheckIn object
        context["has_voted"] = user_has_upvoted(self.request.user, self.object)
        context["can_crosspost_mastodon"] = (
            self.request.user.is_authenticated
            and hasattr(self.request.user, "mastodon_account")
        )
        context["can_crosspost_bluesky"] = (
            self.request.user.is_authenticated
            and hasattr(self.request.user, "bluesky_account")
        )
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


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class GenericCheckInListView(ListView):
    model = WatchCheckIn
    template_name = "watch/watch_checkin_list.html"
    context_object_name = "checkins"

    def get_model(self):
        if self.kwargs["model_name"] == "movie":
            return Movie
        elif self.kwargs["model_name"] == "series":
            return Series
        elif self.kwargs["model_name"] == "season":
            return Season
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
            if model.__name__ == "Season":
                series_id = self.kwargs.get("series_id")
                season_number = self.kwargs.get("season_number")
                object_id = get_object_or_404(
                    Season, series_id=series_id, season_number=season_number
                ).id
            else:
                object_id = self.kwargs["object_id"]  # Get object id from url param

            content_type = ContentType.objects.get_for_model(model)
            checkins = WatchCheckIn.objects.filter(
                user=profile_user, content_type=content_type, object_id=object_id
            )

            if self.request.user.is_authenticated:
                checkins = checkins.filter(
                    Q(visibility="PU") | Q(visible_to=self.request.user)
                )
            else:
                checkins = checkins.filter(visibility="PU")

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
            if model.__name__ == "Season":
                series_id = self.kwargs.get("series_id")
                season_number = self.kwargs.get("season_number")
                object_id = get_object_or_404(
                    Season, series_id=series_id, season_number=season_number
                ).id
            else:
                object_id = self.kwargs["object_id"]  # Get object id from url param

            context["checkins"] = (
                self.get_queryset()
            )  # Use the queryset method to handle status filter

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
        elif self.kwargs["model_name"] == "season":
            season = model.objects.get(pk=object_id)
            roles = {}
            for season_role in season.seasonroles.all():
                if season_role.role.name not in roles:
                    roles[season_role.role.name] = []
                d = season_role.alt_name or season_role.creator.name
                roles[season_role.role.name].append((season_role.creator, d))
            context["roles"] = roles
            context["object"] = season

        include_mathjax, include_mermaid = check_required_js(context["checkins"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        context["is_blocked"] = (
            Block.objects.filter(
                blocker=profile_user, blocked=self.request.user
            ).exists()
            if self.request.user.is_authenticated
            else False
        )

        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
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
        elif self.kwargs["model_name"] == "season":
            return Season
        else:
            return None

    def get_queryset(self):
        model = self.get_model()
        if model is None:
            return WatchCheckIn.objects.none()

        content_type = ContentType.objects.get_for_model(model)
        if self.kwargs["model_name"] == "season":
            series_id = self.kwargs.get("series_id")
            season_number = self.kwargs.get("season_number")
            object_id = get_object_or_404(
                Season, series_id=series_id, season_number=season_number
            ).id
        else:
            object_id = self.kwargs["object_id"]  # Get object id from url param

        latest_checkin_subquery = (
            get_visible_checkins(
                self.request.user, WatchCheckIn, content_type, object_id
            )
            .filter(user=OuterRef("user"))
            .order_by("-timestamp")
        )

        checkins = (
            get_visible_checkins(
                self.request.user, WatchCheckIn, content_type, object_id
            )
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
            get_visible_checkins(
                self.request.user, WatchCheckIn, content_type, object_id
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
        for checkin in checkins:
            checkin.total_checkins = user_checkin_count_dict.get(
                checkin.user.username, 0
            )

        return checkins

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        model = self.get_model()
        if model is not None:
            if model.__name__ == "Season":
                series_id = self.kwargs.get("series_id")
                season_number = self.kwargs.get("season_number")
                context["object"] = get_object_or_404(
                    Season, series_id=series_id, season_number=season_number
                )
            else:
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

        elif context["model_name"] == "season":
            series_id = self.kwargs.get("series_id")
            season_number = self.kwargs.get("season_number")
            season = model.objects.get(series_id=series_id, season_number=season_number)
            roles = {}
            for season_role in season.seasonroles.all():
                if season_role.role.name not in roles:
                    roles[season_role.role.name] = []
                d = season_role.alt_name or season_role.creator.name
                roles[season_role.role.name].append((season_role.creator, d))

        context["roles"] = roles

        include_mathjax, include_mermaid = check_required_js(context["page_obj"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid
        return context


@method_decorator(ratelimit(key="ip", rate="100/m", block=True), name="dispatch")
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

        latest_checkin_subquery = get_visible_checkins(
            self.request.user,
            WatchCheckIn,
            OuterRef("content_type"),
            OuterRef("object_id"),
            checkin_user=profile_user,
        ).order_by("-timestamp")

        checkins = (
            WatchCheckIn.objects.filter(user=profile_user)
            .annotate(
                latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
            )
            .filter(timestamp=F("latest_checkin"))
        )

        if self.request.user.is_authenticated:
            checkins = checkins.filter(
                Q(visibility="PU") | Q(visible_to=self.request.user)
            )
        else:
            checkins = checkins.filter(visibility="PU")

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

        # Filtering by year
        year = self.request.GET.get("year", "")
        month = self.request.GET.get("month", "")
        if year:
            checkins = checkins.filter(timestamp__year=year)
        if month:
            checkins = checkins.filter(timestamp__month=month)


        # Adding count of check-ins for each movie or series 
        user_checkin_counts = (
            get_visible_checkins(
                self.request.user,
                WatchCheckIn,
                checkin_user=profile_user,
            )
            .values("content_type", "object_id")
            .annotate(total_checkins=Count("id") - 1)
        )

        # Convert to a dictionary for easier lookup
        user_checkin_count_dict = {
            (item["content_type"], item["object_id"]): item["total_checkins"]
            for item in user_checkin_counts
        }

        # Annotate the checkins queryset with total_checkins for each content-object
        for checkin in checkins:
            checkin.checkin_count = user_checkin_count_dict.get(
                (checkin.content_type_id, checkin.object_id), 0
            )
        
        # Statistics for books per status
        status_order = ["watched", "rewatched", "watching", "rewatchting", "to_watch", "paused", "abandoned"]
        status_display_map = dict(WatchCheckIn.STATUS_CHOICES)

        status_counts = (
            checkins.values("status")
            .annotate(
                book_count=Count("object_id", distinct=True)  # Count unique books
            )
            .order_by("status")
        )

        # Convert status_counts into a dictionary for easier lookup
        status_count_dict = {item["status"]: item["book_count"] for item in status_counts}

        # Build a dictionary with display names as keys, ordered by status_order
        self.status_stats = {
            status_display_map[status]: status_count_dict.get(status, 0)
            for status in status_order
            if status_count_dict.get(status, 0) > 0  # Include only non-zero counts
        }

        return checkins

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        profile_user = get_object_or_404(User, username=self.kwargs["username"])
        context["profile_user"] = profile_user

        context["order"] = self.request.GET.get("order", "-timestamp")
        context["layout"] = self.request.GET.get("layout", "list")
        context["status"] = status = self.request.GET.get("status", "")
        context["year"] = self.request.GET.get("year", "")
        # Extracting the list of years and months
        checkin_queryset = WatchCheckIn.objects.filter(user=profile_user).distinct()

        # Apply the status filter if it's set
        if status:
            if status == "watched_rewatched":
                checkin_queryset = checkin_queryset.filter(
                    Q(status="watched") | Q(status="rewatched")
                )
            elif status == "watching_rewatching":
                checkin_queryset = checkin_queryset.filter(
                    Q(status="watching") | Q(status="rewatching")
                )
            else:
                checkin_queryset = checkin_queryset.filter(status=status)

        years = checkin_queryset.dates("timestamp", "year")
        # Create a dictionary to store months for each year
        months_by_year = {}
        for year in years:
            months = checkin_queryset.filter(timestamp__year=year.year).dates(
                "timestamp", "month"
            )
            months_by_year[year.year] = [month.month for month in months]

        context["years"] = [year.year for year in years]
        context["months_by_year"] = months_by_year

        context["status_stats"] = self.status_stats


        include_mathjax, include_mermaid = check_required_js(context["page_obj"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        context["is_blocked"] = (
            Block.objects.filter(
                blocker=profile_user, blocked=self.request.user
            ).exists()
            if self.request.user.is_authenticated
            else False
        )

        return context


#########
# Genre #
#########
@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
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
            .annotate(
                annotated_earliest_release_date=Min(
                    "region_release_dates__release_date"
                )
            )
            .order_by("annotated_earliest_release_date")
        )
        context["series"] = Series.objects.filter(genres=genre).order_by(
            "-release_date"
        )

        return context


class GenreAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
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


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class CollectionDetailView(DetailView):
    model = Collection
    template_name = "watch/collection_detail.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # contributors
        context["contributors"] = get_contributors(self.object)

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


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class MovieHistoryView(LoginRequiredMixin, HistoryViewMixin, DetailView):
    model = Movie
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class SeriesHistoryView(LoginRequiredMixin, HistoryViewMixin, DetailView):
    model = Series
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class SeasonHistoryView(LoginRequiredMixin, HistoryViewMixin, DetailView):
    model = Season
    template_name = "entity/history.html"

    def get_object(self):
        series_id = self.kwargs.get("series_id")
        season_number = self.kwargs.get("season_number")
        return get_object_or_404(
            Season, series_id=series_id, season_number=season_number
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class EpisodeHistoryView(LoginRequiredMixin, HistoryViewMixin, DetailView):
    model = Episode
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context

    def get_object(self):
        # Get the series_id and season_episode string from the URL parameters
        series_id = self.kwargs.get("series_id")
        season_number = self.kwargs.get("season_number")
        season_id = get_object_or_404(
            Season, series_id=series_id, season_number=season_number
        ).id
        episode_number = self.kwargs.get("episode_number")

        # Fetch the Episode object based on series_id, season, and episode
        return get_object_or_404(
            Episode,
            series_id=series_id,
            season_id=season_id,
            episode=episode_number,
        )


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class CollectionHistoryView(LoginRequiredMixin, HistoryViewMixin, DetailView):
    model = Collection
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


################
# Autocomplete #
################


class MovieAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Movie.objects.none()

        qs = Movie.objects.all()

        if self.q:
            qs = qs.filter(title__icontains=self.q)

        return qs.order_by("title")

    def get_result_label(self, item):
        # Fetch the earliest release date for the movie
        earliest_release_date = item.region_release_dates.order_by(
            "release_date"
        ).first()
        # Format the label as {title} (release_date)
        release_date_str = (
            earliest_release_date.release_date if earliest_release_date else "No Date"
        )
        return f"{item.title} ({release_date_str})"


class SeriesAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Series.objects.none()

        qs = Series.objects.all()

        if self.q:
            qs = qs.filter(title__icontains=self.q)

        return qs.order_by("title")
