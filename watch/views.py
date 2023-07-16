from collections import defaultdict

from dal import autocomplete
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import F, OuterRef, Prefetch, Q, Subquery
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from write.forms import CommentForm, RepostForm
from write.models import Comment, ContentInList

from .forms import (
    EpisodeCastFormSet,
    EpisodeForm,
    EpisodeRoleFormSet,
    MovieCastFormSet,
    MovieForm,
    MovieRoleFormSet,
    SeriesForm,
    SeriesRoleFormSet,
    WatchCheckInForm,
)
from .models import (
    Episode,
    EpisodeCast,
    Movie,
    MovieRole,
    Series,
    SeriesRole,
    Studio,
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
        else:
            data["movieroles"] = MovieRoleFormSet(instance=self.object)
            data["moviecasts"] = MovieCastFormSet(instance=self.object)

        return data

    def form_valid(self, form):
        context = self.get_context_data()
        movierole = context["movieroles"]
        moviecast = context["moviecasts"]
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
        return super().form_valid(form)


class MovieDetailView(DetailView):
    model = Movie
    template_name = "watch/movie_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        movie = get_object_or_404(Movie, pk=self.kwargs["pk"])

        content_type = ContentType.objects.get_for_model(Movie)
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
        )

        context["lists_containing_movie"] = lists_containing_movie

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
        else:
            data["movieroles"] = MovieRoleFormSet(instance=self.object)
            data["moviecasts"] = MovieCastFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        movierole = context["movieroles"]
        moviecast = context["moviecasts"]
        with transaction.atomic():
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if movierole.is_valid():
                movierole.instance = self.object
                movierole.save()
            if moviecast.is_valid():
                moviecast.instance = self.object
                moviecast.save()
        return super().form_valid(form)


class MovieCastDetailView(DetailView):
    model = Movie
    context_object_name = "movie"
    template_name = "watch/movie_cast_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context[
            "moviecasts"
        ] = self.object.moviecasts.all()  # Update with your correct related name
        context["moviestaffs"] = self.object.movieroles.all()

        return context


class StudioCreateView(LoginRequiredMixin, CreateView):
    model = Studio
    # form_class = StudioForm
    fields = [
        "name",
        "romanized_name",
        "history",
        "location",
        "website",
        "founded_date",
        "closed_date",
    ]
    template_name = "watch/studio_create.html"

    def get_success_url(self):
        return reverse_lazy("watch:studio_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class StudioDetailView(DetailView):
    model = Studio
    template_name = "watch/studio_detail.html"
    context_object_name = "studio"


class StudioAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Studio.objects.none()

        qs = Studio.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class WatchListView(TemplateView):
    template_name = "watch/watch_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["movies"] = Movie.objects.all().order_by("-created_at")[:12]
        context["series"] = Series.objects.all().order_by("-created_at")[:12]
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
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if seriesrole.is_valid():
                seriesrole.instance = self.object
                seriesrole.save()
        return super().form_valid(form)


class SeriesDetailView(DetailView):
    model = Series
    template_name = "watch/series_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        content_type = ContentType.objects.get_for_model(Series)
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
        )

        context["lists_containing_series"] = lists_containing_series

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
        with transaction.atomic():
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if seriesrole.is_valid():
                seriesrole.instance = self.object
                seriesrole.save()

        return super().form_valid(form)


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
            "person", "role"
        )

        # Prepare data structure for the HTML
        series_casts = defaultdict(list)
        for cast in casts:
            series_casts[cast.person].append(
                {
                    "character_name": cast.character_name,
                    "role": cast.role,
                    "episode_title": cast.episode.title,
                    "episode_id": cast.episode.id,
                    "release_date": cast.episode.release_date,
                }
            )

        context["series_casts"] = dict(series_casts)
        context["series_staffs"] = self.object.seriesroles.all()
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


class EpisodeDetailView(DetailView):
    model = Episode
    template_name = "watch/episode_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        episode = get_object_or_404(Episode, pk=self.kwargs["pk"])
        context["episodecasts"] = episode.episodecasts.all()

        return context


class EpisodeUpdateView(LoginRequiredMixin, UpdateView):
    model = Episode
    form_class = EpisodeForm
    template_name = "watch/episode_update.html"

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


class EpisodeCastDetailView(DetailView):
    model = Episode
    context_object_name = "episode"
    template_name = "watch/episode_cast_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context[
            "episodecasts"
        ] = self.object.episodecasts.all()  # Update with your correct related name
        return context


###########
# Checkin #
###########


class WatchCheckInCreateView(LoginRequiredMixin, CreateView):
    model = WatchCheckIn
    form_class = WatchCheckInForm
    template_name = "watch/checkin_create.html"

    def form_valid(self, form):
        movie = get_object_or_404(
            movie, pk=self.kwargs.get("movie_id")
        )  # Fetch the movie based on URL parameter
        form.instance.movie = movie
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("watch:watch_checkin_detail", kwargs={"pk": self.object.pk})


class WatchCheckInDetailView(DetailView):
    model = WatchCheckIn
    template_name = "watch/watch_checkin_detail.html"
    context_object_name = "checkin"  # This name will be used in your template

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = Comment.objects.filter(
            content_type=ContentType.objects.get_for_model(self.object),
            object_id=self.object.id,
        )
        context["comment_form"] = CommentForm()
        context["repost_form"] = RepostForm()
        context["app_label"] = self.object._meta.app_label
        context["object_type"] = self.object._meta.model_name.lower()

        return context


class WatchCheckInUpdateView(LoginRequiredMixin, UpdateView):
    model = WatchCheckIn
    form_class = WatchCheckInForm
    template_name = "watch/watch_checkin_update.html"

    def get_success_url(self):
        return reverse_lazy("watch:watch_checkin_detail", kwargs={"pk": self.object.pk})


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
        user = get_object_or_404(
            User, username=self.kwargs["username"]
        )  # Get user from url param
        model = self.get_model()
        if model is None:
            checkins = WatchCheckIn.objects.none()
        else:
            content_type = ContentType.objects.get_for_model(model)
            object_id = self.kwargs["object_id"]  # Get object id from url param
            checkins = WatchCheckIn.objects.filter(
                user=user, content_type=content_type, object_id=object_id
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
        user = get_object_or_404(User, username=self.kwargs["username"])
        context["user"] = user
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
            context["object"] = model.objects.get(
                pk=object_id
            )  # Get the object details

        context["model_name"] = self.kwargs.get("model_name", "movie")

        return context


class GenericCheckInAllListView(ListView):
    model = WatchCheckIn
    template_name = "watch/watch_checkin_list_all.html"
    context_object_name = "checkins"

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
        return context


class GenericCheckInUserListView(ListView):
    """
    All latest check-ins from a given user of all movies and series.
    """

    model = WatchCheckIn
    template_name = "watch/watch_checkin_list_user.html"
    context_object_name = "checkins"

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs["username"])

        latest_checkin_subquery = WatchCheckIn.objects.filter(
            user=user,
            content_type=OuterRef("content_type"),
            object_id=OuterRef("object_id"),
        ).order_by("-timestamp")

        checkins = (
            WatchCheckIn.objects.filter(user=user)
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

        user = get_object_or_404(User, username=self.kwargs["username"])
        context["user"] = user

        context["order"] = self.request.GET.get(
            "order", "-timestamp"
        )  # Default is '-timestamp'

        context["status"] = self.request.GET.get("status", "")

        return context
