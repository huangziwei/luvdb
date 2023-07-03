from dal import autocomplete
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import F, OuterRef, Prefetch, Q, Subquery
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from write.forms import CommentForm, RepostForm
from write.models import Comment

from .forms import (
    MovieCastFormSet,
    MovieForm,
    MovieRoleFormSet,
    SeriesForm,
    SeriesRoleFormSet,
)
from .models import Movie, MovieRole, Series, SeriesRole, Studio

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

        # context["checkin_form"] = MovieCheckInForm(
        #     initial={"movie": self.object, "user": self.request.user}
        # )

        # # Fetch the latest check-in from each user.
        # latest_checkin_subquery = MovieCheckIn.objects.filter(
        #     movie=self.object, user=OuterRef("user")
        # ).order_by("-timestamp")
        # checkins = (
        #     MovieCheckIn.objects.filter(movie=self.object)
        #     .annotate(
        #         latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
        #     )
        #     .filter(timestamp=F("latest_checkin"))
        # ).order_by("-timestamp")[:5]

        # context["checkins"] = checkins

        # # Movie check-in status counts, considering only latest check-in per user
        # latest_checkin_status_subquery = (
        #     MovieCheckIn.objects.filter(movie=self.object, user=OuterRef("user"))
        #     .order_by("-timestamp")
        #     .values("status")[:1]
        # )
        # latest_checkins = (
        #     MovieCheckIn.objects.filter(movie=self.object)
        #     .annotate(latest_checkin_status=Subquery(latest_checkin_status_subquery))
        #     .values("user", "latest_checkin_status")
        #     .distinct()
        # )

        # not_started_count = sum(
        #     1
        #     for item in latest_checkins
        #     if item["latest_checkin_status"] == "not_started"
        # )
        # watching_count = sum(
        #     1 for item in latest_checkins if item["latest_checkin_status"] == "watching"
        # )
        # finished_count = sum(
        #     1 for item in latest_checkins if item["latest_checkin_status"] == "finished"
        # )

        # # Add status counts to context
        # context.update(
        #     {
        #         "not_started_count": not_started_count,
        #         "watching_count": watching_count,
        #         "finished_count": finished_count,
        #         "checkins": checkins,
        #     }
        # )

        return context

    # def post(self, request, *args, **kwargs):
    #     self.object = self.get_object()
    #     form = MovieCheckInForm(
    #         data=request.POST,
    #         initial={
    #             "movie": self.object,
    #             "user": request.user,
    #             "comments_enabled": True,
    #         },
    #     )
    #     if form.is_valid():
    #         movie_check_in = form.save(commit=False)
    #         movie_check_in.user = request.user  # Set the user manually here
    #         movie_check_in.save()
    #     else:
    #         print(form.errors)

    #     return redirect(self.object.get_absolute_url())


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
    context_object_name = "studio"  # Default is "object"


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
        context["movies"] = Movie.objects.all().order_by("-created_at")
        context["series"] = Series.objects.all().order_by("-created_at")
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
        series = get_object_or_404(Series, pk=self.kwargs["pk"])

        # context["checkin_form"] = MovieCheckInForm(
        #     initial={"movie": self.object, "user": self.request.user}
        # )

        # # Fetch the latest check-in from each user.
        # latest_checkin_subquery = MovieCheckIn.objects.filter(
        #     movie=self.object, user=OuterRef("user")
        # ).order_by("-timestamp")
        # checkins = (
        #     MovieCheckIn.objects.filter(movie=self.object)
        #     .annotate(
        #         latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
        #     )
        #     .filter(timestamp=F("latest_checkin"))
        # ).order_by("-timestamp")[:5]

        # context["checkins"] = checkins

        # # Movie check-in status counts, considering only latest check-in per user
        # latest_checkin_status_subquery = (
        #     MovieCheckIn.objects.filter(movie=self.object, user=OuterRef("user"))
        #     .order_by("-timestamp")
        #     .values("status")[:1]
        # )
        # latest_checkins = (
        #     MovieCheckIn.objects.filter(movie=self.object)
        #     .annotate(latest_checkin_status=Subquery(latest_checkin_status_subquery))
        #     .values("user", "latest_checkin_status")
        #     .distinct()
        # )

        # not_started_count = sum(
        #     1
        #     for item in latest_checkins
        #     if item["latest_checkin_status"] == "not_started"
        # )
        # watching_count = sum(
        #     1 for item in latest_checkins if item["latest_checkin_status"] == "watching"
        # )
        # finished_count = sum(
        #     1 for item in latest_checkins if item["latest_checkin_status"] == "finished"
        # )

        # # Add status counts to context
        # context.update(
        #     {
        #         "not_started_count": not_started_count,
        #         "watching_count": watching_count,
        #         "finished_count": finished_count,
        #         "checkins": checkins,
        #     }
        # )

        return context

    # def post(self, request, *args, **kwargs):
    #     self.object = self.get_object()
    #     form = MovieCheckInForm(
    #         data=request.POST,
    #         initial={
    #             "movie": self.object,
    #             "user": request.user,
    #             "comments_enabled": True,
    #         },
    #     )
    #     if form.is_valid():
    #         movie_check_in = form.save(commit=False)
    #         movie_check_in.user = request.user  # Set the user manually here
    #         movie_check_in.save()
    #     else:
    #         print(form.errors)

    #     return redirect(self.object.get_absolute_url())


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
