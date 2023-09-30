from datetime import timedelta

from dal import autocomplete
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count, F, Max, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.html import format_html
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
    GameReleaseDateFormSet,
    GameRoleFormSet,
    GameSeriesForm,
    WorkForm,
    WorkRoleFormSet,
)
from .models import Game, GameCheckIn, GameSeries, Genre, Platform, Work

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

        # Manually check validity of each form in the formset.
        if not all(workrole_form.is_valid() for workrole_form in workrole):
            return self.form_invalid(form)

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
        grouped_roles = {}
        for role in work.workrole_set.all():
            if role.role.name not in grouped_roles:
                grouped_roles[role.role.name] = []
            alt_name_or_person_name = role.alt_name or role.person.name
            grouped_roles[role.role.name].append((role.person, alt_name_or_person_name))
        context["grouped_roles"] = grouped_roles

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

        # Manually check validity of each form in the formset.
        if not all(workrole_form.is_valid() for workrole_form in workrole):
            return self.form_invalid(form)

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
            data["regionreleasedates"] = GameReleaseDateFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["gameroles"] = GameRoleFormSet(instance=self.object)
            data["gamecasts"] = GameCastFormSet(instance=self.object)
            data["regionreleasedates"] = GameReleaseDateFormSet(instance=self.object)

        return data

    def form_valid(self, form):
        context = self.get_context_data()
        gamerole = context["gameroles"]
        gamecast = context["gamecasts"]
        regionreleasedates = context["regionreleasedates"]

        # Manually check validity of each form in the formset.
        if not all(gamerole_form.is_valid() for gamerole_form in gamerole):
            return self.form_invalid(form)

        if not all(gamecast_form.is_valid() for gamecast_form in gamecast):
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
            if gamerole.is_valid():
                gamerole.instance = self.object
                gamerole.save()
            if gamecast.is_valid():
                gamecast.instance = self.object
                gamecast.save()
            if regionreleasedates.is_valid():
                regionreleasedates.instance = self.object
                regionreleasedates.save()
            else:
                print(regionreleasedates.errors)

        return super().form_valid(form)


class GameDetailView(DetailView):
    model = Game
    template_name = "play/game_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        game = get_object_or_404(Game, pk=self.kwargs["pk"])
        grouped_roles = {}
        for role in game.gameroles.all():
            if role.role.name not in grouped_roles:
                grouped_roles[role.role.name] = []
            alt_name_or_person_name = role.alt_name or role.person.name
            grouped_roles[role.role.name].append((role.person, alt_name_or_person_name))
        context["grouped_roles"] = grouped_roles

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

        # Get the count of check-ins for each user for this game
        user_checkin_counts = (
            GameCheckIn.objects.filter(game=self.object)
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
        ).order_by("luv_list__title")

        context["lists_containing_game"] = lists_containing_game

        # Fetch the latest check-in from the current user for this book
        if self.request.user.is_authenticated:
            latest_user_checkin = (
                GameCheckIn.objects.filter(
                    game=self.object,
                    user=self.request.user,
                )
                .order_by("-timestamp")
                .first()
            )
            if latest_user_checkin is not None:
                context["latest_user_status"] = latest_user_checkin.status
            else:
                context["latest_user_status"] = "to_play"
        else:
            context["latest_user_status"] = "to_play"

        context["ordered_release_dates"] = game.region_release_dates.all().order_by(
            "release_date"
        )

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
            data["regionreleasedates"] = GameReleaseDateFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["gameroles"] = GameRoleFormSet(instance=self.object)
            data["gamecasts"] = GameCastFormSet(instance=self.object)
            data["regionreleasedates"] = GameReleaseDateFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        gamerole = context["gameroles"]
        gamecast = context["gamecasts"]
        regionreleasedates = context["regionreleasedates"]

        # Manually check validity of each form in the formset.
        if not all(gamerole_form.is_valid() for gamerole_form in gamerole):
            return self.form_invalid(form)

        if not all(gamecast_form.is_valid() for gamecast_form in gamecast):
            return self.form_invalid(form)

        if not all(
            region_release_date_form.is_valid()
            for region_release_date_form in regionreleasedates
        ):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if gamerole.is_valid():
                gamerole.instance = self.object
                gamerole.save()
            if gamecast.is_valid():
                gamecast.instance = self.object
                gamecast.save()
            if regionreleasedates.is_valid():
                regionreleasedates.instance = self.object
                regionreleasedates.save()
            else:
                print(regionreleasedates.errors)
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
        context["gamecrew"] = self.object.gameroles.all()
        return context


class PlatformCreateView(LoginRequiredMixin, CreateView):
    model = Platform
    fields = [
        "name",
        "other_names",
        "website",
        "wikipedia",
        "notes",
    ]
    template_name = "play/platform_create.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["other_names"].widget = forms.TextInput()
        return form

    def get_success_url(self):
        return reverse_lazy("play:platform_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class PlatformDetailView(DetailView):
    model = Platform
    template_name = "play/platform_detail.html"
    context_object_name = "platform"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sorted_games"] = self.object.games.all().order_by("release_date")
        return context


class PlatformUpdateView(LoginRequiredMixin, UpdateView):
    model = Platform
    fields = [
        "name",
        "other_names",
        "website",
        "wikipedia",
        "notes",
    ]
    template_name = (
        "play/platform_update.html"  # Change the template name as per your requirement
    )

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["other_names"].widget = forms.TextInput()
        return form

    def get_success_url(self):
        return reverse_lazy("play:platform_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class PlatformAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Platform.objects.none()

        qs = Platform.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

            return qs

        return Platform.objects.none()


class WorkAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Work.objects.none()

        qs = Work.objects.all()

        if self.q:
            qs = qs.filter(
                Q(title__icontains=self.q) | Q(other_titles__icontains=self.q)
            )
            print(f"Filtered qs: {qs}")  # Debugging print

            return qs

        return Work.objects.none()

    def get_result_label(self, item):
        # Get the year from the publication_date
        release_year = (
            item.first_release_date[:4] if item.first_release_date else "Unknown"
        )

        # Format the label
        label = format_html("{} ({})", item.title, release_year)

        return label


class GameCheckInDetailView(DetailView):
    model = GameCheckIn
    template_name = "play/game_checkin_detail.html"
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

        checkin_count = GameCheckIn.objects.filter(
            user=self.object.user,
            game=self.object.game.id,
        ).count()
        context["checkin_count"] = checkin_count - 1

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
        return reverse_lazy("play:game_detail", kwargs={"pk": self.object.game.pk})


class GameCheckInListView(ListView):
    model = GameCheckIn
    template_name = "play/game_checkin_list.html"
    context_object_name = "checkins"

    def get_queryset(self):
        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        status = self.request.GET.get("status")  # Get status from query params
        profile_user = get_object_or_404(
            User, username=self.kwargs["username"]
        )  # Get user from url param
        game_id = self.kwargs["game_id"]  # Get game id from url param

        queryset = GameCheckIn.objects.filter(user=profile_user, game__id=game_id)

        # if status is specified, filter by status
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by(order)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super().get_context_data(**kwargs)
        game = get_object_or_404(Game, pk=self.kwargs["game_id"])
        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        status = self.request.GET.get("status")  # Get status from query params
        profile_user = get_object_or_404(User, username=self.kwargs["username"])
        context["profile_user"] = profile_user
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

        grouped_roles = {}
        for role in game.gameroles.all():
            if role.role.name not in grouped_roles:
                grouped_roles[role.role.name] = []
            alt_name_or_person_name = role.alt_name or role.person.name
            grouped_roles[role.role.name].append((role.person, alt_name_or_person_name))
        context["grouped_roles"] = grouped_roles

        # Get the game details
        context["game"] = game
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
        game = get_object_or_404(Game, pk=self.kwargs["game_id"])
        # Get the game details
        context["game"] = game
        context["order"] = self.request.GET.get(
            "order", "-timestamp"
        )  # Default is '-timestamp'

        grouped_roles = {}
        for role in game.gameroles.all():
            if role.role.name not in grouped_roles:
                grouped_roles[role.role.name] = []
            alt_name_or_person_name = role.alt_name or role.person.name
            grouped_roles[role.role.name].append((role.person, alt_name_or_person_name))
        context["grouped_roles"] = grouped_roles

        return context


class GameCheckInUserListView(ListView):
    """
    All latest check-ins from a given user of all games.
    """

    model = GameCheckIn
    template_name = "play/game_checkin_list_user.html"
    context_object_name = "checkins"

    def get_queryset(self):
        profile_user = get_object_or_404(User, username=self.kwargs["username"])

        latest_checkin_subquery = GameCheckIn.objects.filter(
            user=OuterRef("user"), game=OuterRef("game")
        ).order_by("-timestamp")

        checkins = (
            GameCheckIn.objects.filter(user=profile_user)
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

        profile_user = get_object_or_404(User, username=self.kwargs["username"])
        context["profile_user"] = profile_user

        context["order"] = self.request.GET.get(
            "order", "-timestamp"
        )  # Default is '-timestamp'

        context["status"] = self.request.GET.get("status", "")

        return context


class PlayListView(ListView):
    model = Game
    template_name = "play/play_list.html"

    def get_queryset(self):
        # Getting recent games
        recent_games = Game.objects.all().order_by("-created_at")[:12]

        # Getting trending games based on checkins in the past week
        recent_date = timezone.now() - timedelta(days=7)
        trending_games = (
            Game.objects.annotate(
                checkins=Count(
                    "gamecheckin",
                    filter=Q(gamecheckin__timestamp__gte=recent_date),
                    distinct=True,
                ),
                latest_checkin=Max(
                    "gamecheckin__timestamp",
                    filter=Q(gamecheckin__timestamp__gte=recent_date),
                ),
            )
            .exclude(checkins=0)
            .order_by("-latest_checkin")[:12]
        )

        return {
            "recent_games": recent_games,
            "trending_games": trending_games,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Existing game list based on the model's creation date
        context["games"] = Game.objects.all().order_by("-created_at")[:12]

        # Get the genres
        context["genres"] = (
            Genre.objects.filter(Q(play_works__isnull=False))
            .order_by("name")
            .distinct()
        )

        # Get the recent and trending games
        queryset = self.get_queryset()
        context["recent_games"] = queryset["recent_games"]
        context["trending_games"] = queryset["trending_games"]

        # Additional context for the statistics
        context["works_count"] = Work.objects.count()
        context["games_count"] = Game.objects.count()

        return context


class PlayListAllView(ListView):
    model = Game
    template_name = "play/play_list_all.html"

    def get_queryset(self):
        # Getting recent games
        games = Game.objects.all().order_by("-created_at")

        return {
            "games": games,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Existing game list based on the model's creation date
        context["games"] = Game.objects.all().order_by("-created_at")

        # Get the genres
        context["genres"] = (
            Genre.objects.filter(Q(play_works__isnull=False))
            .order_by("name")
            .distinct()
        )

        # Get the recent and trending games
        queryset = self.get_queryset()
        context["games"] = queryset["games"]

        # Additional context for the statistics
        context["works_count"] = Work.objects.count()
        context["games_count"] = Game.objects.count()

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
