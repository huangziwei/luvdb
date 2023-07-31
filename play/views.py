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
    UpdateView,
)

from write.forms import CommentForm, RepostForm
from write.models import Comment, ContentInList

from .forms import (
    GameCastFormSet,
    GameCheckInForm,
    GameForm,
    GameInSeriesFormSet,
    GameRoleFormSet,
    GameSeriesForm,
    WorkForm,
    WorkRoleFormSet,
)
from .models import (
    Developer,
    Game,
    GameCheckIn,
    GamePublisher,
    GameRole,
    GameSeries,
    Genre,
    Platform,
    Work,
)

User = get_user_model()


class WorkCreateView(LoginRequiredMixin, CreateView):
    model = Work
    form_class = WorkForm
    template_name = "play/work_create.html"

    def get_success_url(self):
        return reverse_lazy("play:work_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        context = self.get_context_data()
        workrole = context["workroles"]
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if workrole.is_valid():
                workrole.instance = self.object
                workrole.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["workroles"] = WorkRoleFormSet(self.request.POST, instance=self.object)
        else:
            data["workroles"] = WorkRoleFormSet(instance=self.object)
        return data


class WorkDetailView(DetailView):
    model = Work
    template_name = "play/work_detail.html"
    context_object_name = "work"  # Default is "object"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        work = get_object_or_404(Work, pk=self.kwargs.get("pk"))
        context["games"] = work.games.all().order_by("release_date")
        return context


class WorkUpdateView(LoginRequiredMixin, UpdateView):
    model = Work
    form_class = WorkForm
    template_name = "play/work_update.html"

    def get_success_url(self):
        return reverse_lazy("play:work_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["workroles"] = WorkRoleFormSet(self.request.POST, instance=self.object)
        else:
            data["workroles"] = WorkRoleFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        workrole = context["workroles"]
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if workrole.is_valid():
                workrole.instance = self.object
                workrole.save()
        return super().form_valid(form)


class GameCreateView(LoginRequiredMixin, CreateView):
    model = Game
    form_class = GameForm
    template_name = "play/game_create.html"

    def get_success_url(self):
        return reverse_lazy("play:game_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["gameroles"] = GameRoleFormSet(self.request.POST, instance=self.object)
            data["gamecasts"] = GameCastFormSet(self.request.POST, instance=self.object)
        else:
            data["gameroles"] = GameRoleFormSet(instance=self.object)
            data["gamecasts"] = GameCastFormSet(instance=self.object)

        return data

    def form_valid(self, form):
        context = self.get_context_data()
        gamerole = context["gameroles"]
        gamecast = context["gamecasts"]
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if gamerole.is_valid():
                gamerole.instance = self.object
                gamerole.save()
            if gamecast.is_valid():
                gamecast.instance = self.object
                gamecast.save()
        return super().form_valid(form)


class GameDetailView(DetailView):
    model = Game
    template_name = "play/game_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        game = get_object_or_404(Game, pk=self.kwargs["pk"])

        context["checkin_form"] = GameCheckInForm(
            initial={"game": self.object, "user": self.request.user}
        )

        # Fetch the latest check-in from each user.
        latest_checkin_subquery = GameCheckIn.objects.filter(
            game=self.object, user=OuterRef("user")
        ).order_by("-timestamp")
        checkins = (
            GameCheckIn.objects.filter(game=self.object)
            .annotate(
                latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
            )
            .filter(timestamp=F("latest_checkin"))
        ).order_by("-timestamp")[:5]

        context["checkins"] = checkins

        # Game check-in status counts, considering only latest check-in per user
        latest_checkin_status_subquery = (
            GameCheckIn.objects.filter(game=self.object, user=OuterRef("user"))
            .order_by("-timestamp")
            .values("status")[:1]
        )
        latest_checkins = (
            GameCheckIn.objects.filter(game=self.object)
            .annotate(latest_checkin_status=Subquery(latest_checkin_status_subquery))
            .values("user", "latest_checkin_status")
            .distinct()
        )

        to_play_count = sum(
            1 for item in latest_checkins if item["latest_checkin_status"] == "to_play"
        )
        playing_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["playing", "replaying"]
        )
        played_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["played", "replayed"]
        )

        # Add status counts to context
        context.update(
            {
                "to_play_count": to_play_count,
                "playing_count": playing_count,
                "played_count": played_count,
                "checkins": checkins,
            }
        )

        # Get the ContentType for the Issue model
        game_content_type = ContentType.objects.get_for_model(Game)

        # Query ContentInList instances that have the game as their content_object
        lists_containing_game = ContentInList.objects.filter(
            content_type=game_content_type, object_id=self.object.id
        )

        context["lists_containing_game"] = lists_containing_game

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = GameCheckInForm(
            data=request.POST,
            initial={
                "game": self.object,
                "user": request.user,
                "comments_enabled": True,
            },
        )
        if form.is_valid():
            game_check_in = form.save(commit=False)
            game_check_in.user = request.user  # Set the user manually here
            game_check_in.save()
        else:
            print(form.errors)

        return redirect(self.object.get_absolute_url())


class GameUpdateView(LoginRequiredMixin, UpdateView):
    model = Game
    form_class = GameForm
    template_name = "play/game_update.html"

    def get_success_url(self):
        return reverse_lazy("play:game_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["gameroles"] = GameRoleFormSet(self.request.POST, instance=self.object)
            data["gamecasts"] = GameCastFormSet(self.request.POST, instance=self.object)
        else:
            data["gameroles"] = GameRoleFormSet(instance=self.object)
            data["gamecasts"] = GameCastFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        gamerole = context["gameroles"]
        gamecast = context["gamecasts"]
        with transaction.atomic():
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if gamerole.is_valid():
                gamerole.instance = self.object
                gamerole.save()
            if gamecast.is_valid():
                gamecast.instance = self.object
                gamecast.save()
        return super().form_valid(form)


class GameCastDetailView(DetailView):
    model = Game
    context_object_name = "game"
    template_name = "play/game_cast_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context[
            "gamecasts"
        ] = self.object.gamecasts.all()  # Update with your correct related name
        return context


class DeveloperCreateView(LoginRequiredMixin, CreateView):
    model = Developer
    fields = [
        "name",
        "romanized_name",
        "history",
        "location",
        "website",
        "founded_date",
        "closed_date",
    ]
    template_name = "play/developer_create.html"

    def get_success_url(self):
        return reverse_lazy("play:developer_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class DeveloperDetailView(DetailView):
    model = Developer
    template_name = "play/developer_detail.html"
    context_object_name = "developer"


class DeveloperUpdateView(LoginRequiredMixin, UpdateView):
    model = Developer
    fields = [
        "name",
        "romanized_name",
        "history",
        "location",
        "website",
        "founded_date",
        "closed_date",
    ]
    template_name = "play/developer_update.html"

    def get_success_url(self):
        return reverse_lazy("play:developer_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class PlatformCreateView(LoginRequiredMixin, CreateView):
    model = Platform
    fields = [
        "name",
        "romanized_name",
        "website",
    ]
    template_name = "play/platform_create.html"

    def get_success_url(self):
        return reverse_lazy("play:platform_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class PlatformDetailView(DetailView):
    model = Platform
    template_name = "play/platform_detail.html"
    context_object_name = "platform"  # Default is "object"


class PlatformUpdateView(LoginRequiredMixin, UpdateView):
    model = Platform
    fields = [
        "name",
        "romanized_name",
        "website",
    ]
    template_name = (
        "play/platform_update.html"  # Change the template name as per your requirement
    )

    def get_success_url(self):
        return reverse_lazy("play:platform_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class DeveloperAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Developer.objects.none()

        qs = Developer.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs


class GamePublisherAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return GamePublisher.objects.none()

        qs = GamePublisher.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs


class PlatformAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Platform.objects.none()

        qs = Platform.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs


class WorkAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Work.objects.none()

        qs = Work.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs


class GenreAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Genre.objects.none()

        qs = Genre.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs


class GameCheckInDetailView(DetailView):
    model = GameCheckIn
    template_name = "play/game_checkin_detail.html"
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


class GameCheckInUpdateView(LoginRequiredMixin, UpdateView):
    model = GameCheckIn
    form_class = GameCheckInForm
    template_name = "play/game_checkin_update.html"

    def get_success_url(self):
        return reverse_lazy("play:game_checkin_detail", kwargs={"pk": self.object.pk})


class GameCheckInDeleteView(LoginRequiredMixin, DeleteView):
    model = GameCheckIn
    template_name = "play/game_checkin_delete.html"

    def get_success_url(self):
        return reverse_lazy("play:game_detail", kwargs={"pk": self.object.book.pk})


class GameCheckInListView(ListView):
    model = GameCheckIn
    template_name = "play/game_checkin_list.html"
    context_object_name = "checkins"

    def get_queryset(self):
        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        status = self.request.GET.get("status")  # Get status from query params
        user = get_object_or_404(
            User, username=self.kwargs["username"]
        )  # Get user from url param
        game_id = self.kwargs["game_id"]  # Get game id from url param

        queryset = GameCheckIn.objects.filter(user=user, game__id=game_id)

        # if status is specified, filter by status
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by(order)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super().get_context_data(**kwargs)

        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        status = self.request.GET.get("status")  # Get status from query params
        user = get_object_or_404(User, username=self.kwargs["username"])
        context["user"] = user
        context["order"] = order
        context["status"] = status  # pass the status to the context
        checkins = GameCheckIn.objects.filter(
            user__username=self.kwargs["username"], game__id=self.kwargs["game_id"]
        )

        # if status is specified, filter by status
        if status:
            if status == "played_replayed":
                checkins = checkins.filter(Q(status="played") | Q(status="replayed"))
            elif status == "playing_replaying":
                checkins = checkins.filter(Q(status="playing") | Q(status="replaying"))
            else:
                checkins = checkins.filter(status=status)

        context["checkins"] = checkins.order_by(order)

        # Get the game details
        context["game"] = get_object_or_404(Game, pk=self.kwargs["game_id"])
        return context


class GameCheckInAllListView(ListView):
    model = GameCheckIn
    template_name = "play/game_checkin_list_all.html"
    context_object_name = "checkins"

    def get_queryset(self):
        # Fetch the latest check-in from each user.
        latest_checkin_subquery = GameCheckIn.objects.filter(
            game=self.kwargs["game_id"], user=OuterRef("user")
        ).order_by("-timestamp")

        checkins = (
            GameCheckIn.objects.filter(game=self.kwargs["game_id"])
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
            if status == "played_replayed":
                checkins = checkins.filter(Q(status="played") | Q(status="replayed"))
            elif status == "playing_replaying":
                checkins = checkins.filter(Q(status="playing") | Q(status="replaying"))
            else:
                checkins = checkins.filter(status=status)

        return checkins

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super().get_context_data(**kwargs)

        # Get the game details
        context["game"] = get_object_or_404(Game, pk=self.kwargs["game_id"])
        context["order"] = self.request.GET.get(
            "order", "-timestamp"
        )  # Default is '-timestamp'
        return context


class GameCheckInUserListView(ListView):
    """
    All latest check-ins from a given user of all movies and series.
    """

    model = GameCheckIn
    template_name = "play/game_checkin_list_user.html"
    context_object_name = "checkins"

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs["username"])

        latest_checkin_subquery = GameCheckIn.objects.filter(
            user=OuterRef("user"), game=OuterRef("game")
        ).order_by("-timestamp")

        checkins = (
            GameCheckIn.objects.filter(user=user)
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
            if status == "played_replayed":
                checkins = checkins.filter(Q(status="played") | Q(status="replayed"))
            elif status == "playing_replaying":
                checkins = checkins.filter(Q(status="playing") | Q(status="replaying"))
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


class PlayListView(ListView):
    model = Game
    template_name = "play/play_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["games"] = Game.objects.all().order_by("-created_at")[:12]

        # Include genres with at least one movie or series
        context["genres"] = Genre.objects.filter(Q(play_works__isnull=False)).distinct()
        return context


class GameSeriesCreateView(LoginRequiredMixin, CreateView):
    model = GameSeries
    form_class = GameSeriesForm
    template_name = "play/series_create.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["games"] = GameInSeriesFormSet(self.request.POST)
        else:
            data["games"] = GameInSeriesFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        games = context["games"]
        with transaction.atomic():
            form.instance.created_by = self.request.user
            self.object = form.save()
            if games.is_valid():
                games.instance = self.object
                games.save()
        return super().form_valid(form)


class GameSeriesDetailView(DetailView):
    model = GameSeries
    template_name = "play/series_detail.html"  # Update this


class GameSeriesUpdateView(LoginRequiredMixin, UpdateView):
    model = GameSeries
    form_class = GameSeriesForm
    template_name = "play/series_update.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["games"] = GameInSeriesFormSet(self.request.POST, instance=self.object)
        else:
            data["games"] = GameInSeriesFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        games = context["games"]
        print("Formset data:", self.request.POST)  # Print out the formset POST data.
        if games.is_valid():
            self.object = form.save()
            games.instance = self.object
            games.save()
        else:
            print("Formset errors:", games.errors)  # Print out the formset errors.
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("play:series_detail", kwargs={"pk": self.object.pk})


class GamePublisherCreateView(LoginRequiredMixin, CreateView):
    model = GamePublisher
    fields = [
        "name",
        "romanized_name",
        "history",
        "location",
        "website",
        "founded_date",
        "closed_date",
    ]
    template_name = "play/gamepublisher_create.html"

    def get_success_url(self):
        return reverse_lazy("play:publisher_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class GamePublisherDetailView(DetailView):
    model = GamePublisher
    template_name = "play/gamepublisher_detail.html"
    context_object_name = "gamepublisher"


class GamePublisherUpdateView(LoginRequiredMixin, UpdateView):
    model = GamePublisher
    fields = [
        "name",
        "romanized_name",
        "history",
        "location",
        "website",
        "founded_date",
        "closed_date",
    ]
    template_name = "play/gamepublisher_update.html"

    def get_success_url(self):
        return reverse_lazy("play:publisher_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


#########
# Genre #
#########
class GenreDetailView(DetailView):
    model = Genre
    template_name = "play/genre_detail.html"  # Update with your actual template name
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the genre object
        genre = self.object

        # Get all movies and series associated with this genre
        # and order them by release date
        context["works"] = Work.objects.filter(genres=genre).order_by(
            "-first_release_date"
        )

        return context


class GenreAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Genre.objects.none()

        qs = Genre.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs
