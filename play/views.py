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
from django.utils.html import format_html
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from django_ratelimit.decorators import ratelimit

from activity_feed.models import Block
from discover.views import user_has_upvoted
from entity.views import HistoryViewMixin, get_contributors
from visit.utils import get_locations_with_parents
from write.forms import CommentForm, RepostForm
from write.models import Comment, ContentInList, WebMention
from write.utils_formatting import check_required_js

from .forms import (
    DLCCastFormSet,
    DLCForm,
    DLCRoleFormSet,
    GameCastFormSet,
    GameForm,
    GameInSeriesFormSet,
    GameReleaseDateFormSet,
    GameRoleFormSet,
    GameSeriesForm,
    PlayCheckInForm,
    WorkForm,
    WorkRoleFormSet,
)
from .models import DLC, Game, GameSeries, Genre, Platform, PlayCheckIn, Work

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


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
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
            creatoralt_name_or_creator_name = role.alt_name or role.creator.name
            grouped_roles[role.role.name].append(
                (role.creator, creatoralt_name_or_creator_name)
            )
        context["grouped_roles"] = grouped_roles

        games = (
            work.games.all()
            .annotate(
                annotated_earliest_release_date=Min(
                    "region_release_dates__release_date"
                )
            )
            .order_by("annotated_earliest_release_date")
        )

        context["games"] = games

        # contributors
        context["contributors"] = get_contributors(self.object)

        context["setting_locations_with_parents"] = get_locations_with_parents(
            self.object.setting_locations
        )

        return context


class WorkUpdateView(LoginRequiredMixin, UpdateView):
    model = Work
    form_class = WorkForm
    template_name = "play/work_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

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

        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
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
            creatoralt_name_or_creator_name = role.alt_name or role.creator.name
            grouped_roles[role.role.name].append(
                (role.creator, creatoralt_name_or_creator_name)
            )
        context["grouped_roles"] = grouped_roles

        content_type = ContentType.objects.get_for_model(Game)
        context["checkin_form"] = PlayCheckInForm(
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": self.request.user,
            }
        )

        # Fetch the latest check-in from each user.
        latest_checkin_subquery = PlayCheckIn.objects.filter(
            content_type=content_type.id,
            object_id=self.object.id,
            user=OuterRef("user"),
        ).order_by("-timestamp")
        checkins = (
            PlayCheckIn.objects.filter(
                content_type=content_type.id,
                object_id=self.object.id,
            )
            .annotate(
                latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
            )
            .filter(timestamp=F("latest_checkin"))
        ).order_by("-timestamp")[:5]

        context["checkins"] = checkins

        # Get the count of check-ins for each user for this game
        user_checkin_counts = (
            PlayCheckIn.objects.filter(
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

        # Game check-in status counts, considering only latest check-in per user
        latest_checkin_status_subquery = (
            PlayCheckIn.objects.filter(
                content_type=content_type.id,
                object_id=self.object.id,
                user=OuterRef("user"),
            )
            .order_by("-timestamp")
            .values("status")[:1]
        )
        latest_checkins = (
            PlayCheckIn.objects.filter(
                content_type=content_type.id, object_id=self.object.id
            )
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

        # Query ContentInList instances that have the game as their content_object
        lists_containing_game = ContentInList.objects.filter(
            content_type=content_type, object_id=self.object.id
        ).order_by("luv_list__title")

        context["lists_containing_game"] = lists_containing_game

        # Fetch the latest check-in from the current user for this book
        if self.request.user.is_authenticated:
            latest_user_checkin = (
                PlayCheckIn.objects.filter(
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
                context["latest_user_status"] = "to_play"
        else:
            context["latest_user_status"] = "to_play"

        context["ordered_release_dates"] = game.region_release_dates.all().order_by(
            "release_date"
        )

        # contributors
        context["contributors"] = get_contributors(self.object)

        include_mathjax, include_mermaid = check_required_js(context["checkins"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        context["dlcs"] = game.dlc.all().order_by("release_date")

        if self.object.work:
            context["setting_locations_with_parents"] = get_locations_with_parents(
                self.object.work.setting_locations
            )

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        content_type = ContentType.objects.get_for_model(Game)
        form = PlayCheckInForm(
            data=request.POST,
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
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

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

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


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
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


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class PlatformDetailView(DetailView):
    model = Platform
    template_name = "play/platform_detail.html"
    context_object_name = "platform"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sorted_games"] = (
            self.object.games.all()
            .annotate(
                annotated_earliest_release_date=Min(
                    "region_release_dates__release_date"
                )
            )
            .order_by("annotated_earliest_release_date")
        )

        # contributors
        context["contributors"] = get_contributors(self.object)
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

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

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


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class PlayCheckInDetailView(DetailView):
    model = PlayCheckIn
    template_name = "play/play_checkin_detail.html"
    context_object_name = "checkin"  # This name will be used in your template

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = Comment.objects.filter(
            content_type=ContentType.objects.get_for_model(self.object),
            object_id=self.object.id,
        ).order_by("timestamp")
        context["comment_form"] = CommentForm()
        context["repost_form"] = RepostForm(user=self.request.user)
        context["app_label"] = self.object._meta.app_label
        context["object_type"] = self.object._meta.model_name.lower()

        checkin_count = PlayCheckIn.objects.filter(
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

        obj = self.get_object()
        partial_target_url = f"@{obj.user.username}/play/checkin/{obj.id}/"

        # Filter WebMentions based on the constructed URL
        context["webmentions"] = WebMention.objects.filter(
            target__endswith=partial_target_url
        ).order_by("received_at")

        return context


class PlayCheckInUpdateView(LoginRequiredMixin, UpdateView):
    model = PlayCheckIn
    form_class = PlayCheckInForm
    template_name = "play/play_checkin_update.html"

    def get_success_url(self):
        return reverse_lazy(
            "write:play_checkin_detail",
            kwargs={"pk": self.object.pk, "username": self.object.user.username},
        )


class PlayCheckInDeleteView(LoginRequiredMixin, DeleteView):
    model = PlayCheckIn
    template_name = "play/play_checkin_delete.html"

    def get_success_url(self):
        return reverse_lazy(
            "play:game_detail", kwargs={"pk": self.object.content_object.pk}
        )


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class PlayCheckInListView(ListView):
    model = PlayCheckIn
    template_name = "play/play_checkin_list.html"
    context_object_name = "checkins"

    def get_model(self):
        return Game

    def get_queryset(self):
        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        status = self.request.GET.get("status")  # Get status from query params
        profile_user = get_object_or_404(
            User, username=self.kwargs["username"]
        )  # Get user from url param
        model = self.get_model()
        content_type = ContentType.objects.get_for_model(model)
        object_id = self.kwargs["object_id"]  # Get object id from url param
        checkins = PlayCheckIn.objects.filter(
            user=profile_user, content_type=content_type, object_id=object_id
        )

        # if status is specified, filter by status
        if status:
            if status == "played_replayed":
                checkins = checkins.filter(Q(status="played") | Q(status="replayed"))
            elif status == "playing_replaying":
                checkins = checkins.filter(Q(status="playing") | Q(status="replaying"))
            else:
                checkins = checkins.filter(status=status)

        return checkins.order_by(order)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super().get_context_data(**kwargs)
        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        status = self.request.GET.get("status")  # Get status from query params
        profile_user = get_object_or_404(User, username=self.kwargs["username"])
        context["profile_user"] = profile_user
        context["order"] = order
        context["status"] = status  # pass the status to the context

        model = self.get_model()
        content_type = ContentType.objects.get_for_model(model)
        object_id = self.kwargs["object_id"]
        context["checkins"] = checkins = self.get_queryset()
        context["object"] = model.objects.get(pk=object_id)

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
        game = get_object_or_404(Game, pk=self.kwargs["object_id"])
        for role in game.gameroles.all():
            if role.role.name not in grouped_roles:
                grouped_roles[role.role.name] = []
            creatoralt_name_or_creator_name = role.alt_name or role.creator.name
            grouped_roles[role.role.name].append(
                (role.creator, creatoralt_name_or_creator_name)
            )
        context["grouped_roles"] = grouped_roles

        # Get the game details
        context["game"] = game

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
class PlayCheckInAllListView(ListView):
    model = PlayCheckIn
    template_name = "play/play_checkin_list_all.html"
    context_object_name = "checkins"
    paginate_by = 25

    def get_queryset(self):
        # Fetch the latest check-in from each user.
        content_type = ContentType.objects.get_for_model(Game)
        object_id = self.kwargs["object_id"]
        latest_checkin_subquery = PlayCheckIn.objects.filter(
            content_type=content_type, object_id=object_id, user=OuterRef("user")
        ).order_by("-timestamp")

        checkins = (
            PlayCheckIn.objects.filter(content_type=content_type, object_id=object_id)
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

        status = self.request.GET.get("status", "")
        if status:
            if status == "played_replayed":
                checkins = checkins.filter(Q(status="played") | Q(status="replayed"))
            elif status == "playing_replaying":
                checkins = checkins.filter(Q(status="playing") | Q(status="replaying"))
            else:
                checkins = checkins.filter(status=status)

        # Get the count of check-ins for each user for this game
        user_checkin_counts = (
            PlayCheckIn.objects.filter(content_type=content_type, object_id=object_id)
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
        # Call the base implementation first to get the context
        context = super().get_context_data(**kwargs)
        game = get_object_or_404(Game, pk=self.kwargs["object_id"])
        # Get the game details
        context["game"] = game
        context["order"] = self.request.GET.get(
            "order", "-timestamp"
        )  # Default is '-timestamp'

        grouped_roles = {}
        for role in game.gameroles.all():
            if role.role.name not in grouped_roles:
                grouped_roles[role.role.name] = []
            creatoralt_name_or_creator_name = role.alt_name or role.creator.name
            grouped_roles[role.role.name].append(
                (role.creator, creatoralt_name_or_creator_name)
            )
        context["grouped_roles"] = grouped_roles

        include_mathjax, include_mermaid = check_required_js(context["page_obj"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        return context


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class PlayCheckInUserListView(ListView):
    """
    All latest check-ins from a given user of all games.
    """

    model = PlayCheckIn
    template_name = "play/play_checkin_list_user.html"
    context_object_name = "checkins"
    paginate_by = 25

    def get_queryset(self):
        profile_user = get_object_or_404(User, username=self.kwargs["username"])

        latest_checkin_subquery = PlayCheckIn.objects.filter(
            user=profile_user,
            content_type=OuterRef("content_type"),
            object_id=OuterRef("object_id"),
        ).order_by("-timestamp")

        checkins = (
            PlayCheckIn.objects.filter(user=profile_user)
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

        # Count the check-ins for each game for this user
        user_checkin_counts = (
            PlayCheckIn.objects.filter(user=profile_user)
            .values("content_type", "object_id")
            .annotate(total_checkins=Count("id") - 1)
        )

        # Convert to a dictionary for easier lookup
        user_checkin_count_dict = {
            (item["content_type"], item["object_id"]): item["total_checkins"]
            for item in user_checkin_counts
        }

        # Annotate the checkins queryset with checkin_count for each game
        for checkin in checkins:
            checkin.checkin_count = user_checkin_count_dict.get(
                (checkin.content_type_id, checkin.object_id), 0
            )

        return checkins

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        profile_user = get_object_or_404(User, username=self.kwargs["username"])
        context["profile_user"] = profile_user

        context["order"] = self.request.GET.get("order", "-timestamp")
        context["layout"] = self.request.GET.get("layout", "list")

        context["status"] = self.request.GET.get("status", "")

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


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
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
                    "playcheckin",
                    filter=Q(playcheckin__timestamp__gte=recent_date),
                    distinct=True,
                ),
                latest_checkin=Max(
                    "playcheckin__timestamp",
                    filter=Q(playcheckin__timestamp__gte=recent_date),
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


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class PlayListAllView(LoginRequiredMixin, ListView):
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


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class GameSeriesDetailView(DetailView):
    model = GameSeries
    template_name = "play/game_detail.html"  # Update this

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # contributors
        context["contributors"] = get_contributors(self.object)
        return context


class GameSeriesUpdateView(LoginRequiredMixin, UpdateView):
    model = GameSeries
    form_class = GameSeriesForm
    template_name = "play/game_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

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
        return reverse_lazy("play:game_detail", kwargs={"pk": self.object.pk})


#########
# Genre #
#########
@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class GenreDetailView(DetailView):
    model = Genre
    template_name = "play/genre_detail.html"  # Update with your actual template name
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the genre object
        genre = self.object

        # Get all movies and game associated with this genre
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

        return qs.order_by("name")


#################
# History Views #
#################


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class WorkHistoryView(HistoryViewMixin, DetailView):
    model = Work
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class GameHistoryView(HistoryViewMixin, DetailView):
    model = Game
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class GameSeriesHistoryView(HistoryViewMixin, DetailView):
    model = GameSeries
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class PlatformHistoryView(HistoryViewMixin, DetailView):
    model = Platform
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


class DLCCreateView(LoginRequiredMixin, CreateView):
    model = DLC
    form_class = DLCForm
    template_name = "play/dlc_create.html"

    def get_initial(self):
        initial = super().get_initial()
        game_id = self.kwargs.get("game_id")
        initial["game"] = get_object_or_404(Game, pk=game_id)
        return initial

    def get_form(self, form_class=None):
        form = super(DLCCreateView, self).get_form(form_class)
        form.fields["game"].disabled = True
        return form

    def get_success_url(self):
        game_id = self.kwargs.get("game_id")
        return reverse("play:game_detail", kwargs={"pk": game_id})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["dlcroles"] = DLCRoleFormSet(self.request.POST, instance=self.object)
            data["dlccasts"] = DLCCastFormSet(self.request.POST, instance=self.object)
        else:
            data["dlcroles"] = DLCRoleFormSet(instance=self.object)
            data["dlccasts"] = DLCCastFormSet(instance=self.object)

        return data

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        context = self.get_context_data()
        dlcroles = context["dlcroles"]
        dlccasts = context["dlccasts"]

        # Manually check validity of each form in the formset.
        if not all(dlcrole_form.is_valid() for dlcrole_form in dlcroles):
            return self.form_invalid(form)

        if not all(dlccast_form.is_valid() for dlccast_form in dlccasts):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if dlcroles.is_valid():
                dlcroles.instance = self.object
                dlcroles.save()
            else:
                print(dlcroles.errors)  # print out formset errors
            if dlccasts.is_valid():
                dlccasts.instance = self.object
                dlccasts.save()
            else:
                print(dlccasts.errors)  # print out formset errors
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class DLCDetailView(DetailView):
    model = DLC
    template_name = "play/dlc_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dlc = get_object_or_404(DLC, pk=self.kwargs["pk"])
        context["dlccasts"] = dlc.dlccasts.all()
        # Group dlcroles by their roles
        dlcroles_grouped = defaultdict(list)
        for dlcrole in dlc.dlcroles.all():
            dlcroles_grouped[dlcrole.role].append(dlcrole)

        context["dlcroles"] = dict(dlcroles_grouped)

        # contributors
        context["contributors"] = get_contributors(self.object)
        context["dlcs"] = dlc.game.dlc.all().order_by("release_date")

        return context


class DLCUpdateView(LoginRequiredMixin, UpdateView):
    model = DLC
    form_class = DLCForm
    template_name = "play/dlc_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        game_id = self.kwargs.get("game_id")
        initial["game"] = get_object_or_404(Series, pk=game_id)
        return initial

    def get_form(self, form_class=None):
        form = super(DLCUpdateView, self).get_form(form_class)
        form.fields["game"].disabled = True
        return form

    def get_success_url(self):
        return reverse_lazy(
            "play:dlc_detail",
            kwargs={"pk": self.object.pk, "game_id": self.object.game.pk},
        )

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["dlcroles"] = DLCRoleFormSet(self.request.POST, instance=self.object)
            data["dlccasts"] = DLCCastFormSet(self.request.POST, instance=self.object)
        else:
            data["dlcroles"] = DLCRoleFormSet(instance=self.object)
            data["dlccasts"] = DLCCastFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        dlcroles = context["dlcroles"]
        dlccasts = context["dlccasts"]

        # Manually check validity of each form in the formset.
        if not all(dlcrole_form.is_valid() for dlcrole_form in dlcroles):
            return self.form_invalid(form)

        if not all(dlccast_form.is_valid() for dlccast_form in dlccasts):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if dlcroles.is_valid():
                dlcroles.instance = self.object
                dlcroles.save()
            if dlccasts.is_valid():
                dlccasts.instance = self.object
                dlccasts.save()
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class DLCHistoryView(HistoryViewMixin, DetailView):
    model = DLC
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context
