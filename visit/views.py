import re
from collections import defaultdict
from operator import attrgetter

from dal import autocomplete
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import (
    Case,
    CharField,
    Count,
    F,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from django_ratelimit.decorators import ratelimit

from activity_feed.models import Block
from discover.utils import user_has_upvoted
from entity.models import Company, Creator
from entity.views import HistoryViewMixin, get_contributors
from play.models import Work as GameWork
from read.models import Work as Publicaiton
from scrape.wikipedia import scrape_location
from watch.models import Episode, Movie, Series
from write.forms import CommentForm, RepostForm
from write.models import Comment
from write.utils import get_visible_checkins, get_visible_comments
from write.utils_bluesky import create_bluesky_post
from write.utils_formatting import check_required_js
from write.utils_mastodon import create_mastodon_post

from .forms import LocationForm, VisitCheckInForm
from .models import Location, VisitCheckIn
from .utils import get_parent_locations

User = get_user_model()


class LocationCreateView(LoginRequiredMixin, CreateView):
    model = Location
    form_class = LocationForm
    template_name = "visit/location_create.html"

    def get_success_url(self):
        return reverse_lazy("visit:location_detail", kwargs={"pk": self.object.pk})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["other_names"].widget = forms.TextInput()
        form.fields["address"].widget = forms.TextInput()
        return form

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        if "wiki_url" in request.POST:
            wiki_url = request.POST.get("wiki_url")
            scraped_data = scrape_location(wiki_url)
            if scraped_data:
                # Initialize the form with imported data
                form = self.form_class(initial=scraped_data)
                form.fields["other_names"].widget = forms.TextInput()
                form.fields["address"].widget = forms.TextInput()
                # Render response with initialized form and formsets
                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                    },
                )
            else:
                # Handle case where import fails
                return self.form_invalid(form)
        else:
            return super().post(request, *args, **kwargs)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class LocationDetailView(DetailView):
    model = Location
    template_name = "visit/location_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parent_locations"] = get_parent_locations(self.object)
        if self.object.current_identity:
            context["current_identity_parents"] = get_parent_locations(
                self.object.current_identity
            )

        historical_identities = Location.objects.filter(
            current_identity=self.object
        ).order_by("historical_period")
        context["historical_identities"] = historical_identities

        # Group children by their levels
        children_grouped_by_level_current = defaultdict(list)
        children_grouped_by_level_historical = defaultdict(list)
        for child in self.object.children.all().order_by("name"):
            level = child.level_name
            if child.historical:
                children_grouped_by_level_historical[level].append(child)
            else:
                children_grouped_by_level_current[level].append(child)

        context["children_grouped_by_level_current"] = dict(
            children_grouped_by_level_current
        )
        context["children_grouped_by_level_historical"] = dict(
            children_grouped_by_level_historical
        )

        regex_pattern = r"(?:^|,)" + re.escape(str(self.object.id)) + r"(?:,|$)"
        creators_born_here_persons = (
            Creator.objects.annotate(
                birth_date_order=Case(
                    # Assuming birth_date is a string; adjust the condition if it's stored differently
                    When(
                        birth_date__regex=r"^\?.*$", then=Value(2)
                    ),  # Partial dates get a value of 2
                    When(
                        birth_date__isnull=True, then=Value(3)
                    ),  # Unknown dates get a value of 3
                    default=Value(1),  # Fully known dates get a value of 1
                    output_field=CharField(),
                )
            )
            .filter(
                birth_location_hierarchy__regex=regex_pattern,
                creator_type="person",
            )
            .order_by("birth_date_order", "birth_date", "name")
        )

        creators_born_here_groups = Creator.objects.filter(
            origin_location_hierarchy__regex=regex_pattern,
            creator_type="group",  # Adjust the filter based on your model
        ).order_by("active_years")

        context["creators_born_here_persons"] = creators_born_here_persons
        context["creators_born_here_groups"] = creators_born_here_groups

        context["creators_died_here"] = Creator.objects.filter(
            death_location_hierarchy__regex=regex_pattern
        ).order_by("death_date")
        context["companies_here"] = (
            Company.objects.annotate(
                founded_date_order=Case(
                    # Assuming founded_date is a string; adjust the condition if it's stored differently
                    When(
                        founded_date__regex=r"^\?.*$", then=Value(2)
                    ),  # Partial dates get a value of 2
                    When(
                        founded_date__isnull=True, then=Value(3)
                    ),  # Unknown dates get a value of 3
                    default=Value(1),  # Fully known dates get a value of 1
                    output_field=CharField(),
                )
            )
            .filter(location_hierarchy__regex=regex_pattern)
            .order_by("founded_date_order", "founded_date", "name")
        )

        context["contributors"] = get_contributors(self.object)

        context["movies_filmed_here"] = sorted(
            Movie.objects.filter(filming_locations_hierarchy__regex=regex_pattern),
            key=attrgetter("earliest_release_date"),
        )
        context["movies_set_here"] = sorted(
            Movie.objects.filter(setting_locations_hierarchy__regex=regex_pattern),
            key=attrgetter("earliest_release_date"),
        )

        episodes_filmed_here = Episode.objects.filter(
            filming_locations_hierarchy__regex=regex_pattern
        )
        episodes_set_here = Episode.objects.filter(
            setting_locations_hierarchy__regex=regex_pattern
        )

        series_ids_filmed = episodes_filmed_here.values_list(
            "series", flat=True
        ).distinct()
        series_ids_set = episodes_set_here.values_list("series", flat=True).distinct()
        context["series_filmed_here"] = Series.objects.filter(
            id__in=series_ids_filmed
        ).order_by("title")
        context["series_set_here"] = Series.objects.filter(
            id__in=series_ids_set
        ).order_by("title")

        context["publications_set_here"] = Publicaiton.objects.filter(
            related_locations_hierarchy__regex=regex_pattern
        ).order_by("publication_date")

        context["games_set_here"] = GameWork.objects.filter(
            setting_locations_hierarchy__regex=regex_pattern
        ).order_by("first_release_date")

        # check-ins
        content_type = ContentType.objects.get_for_model(Location)
        context["checkin_form"] = VisitCheckInForm(
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": self.request.user,
            }
        )

        # Fetch the latest check-in from each user.
        latest_checkin_subquery = (
            get_visible_checkins(
                self.request.user, VisitCheckIn, content_type, self.object.id
            )
            .filter(user=OuterRef("user"))
            .order_by("-timestamp")
        )
        checkins = (
            get_visible_checkins(
                self.request.user, VisitCheckIn, content_type, self.object.id
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
                self.request.user, VisitCheckIn, content_type, self.object.id
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
                VisitCheckIn,
                content_type,
                self.object.id,
                checkin_user=OuterRef("user"),
            )
            .order_by("-timestamp")
            .values("status")[:1]
        )
        latest_checkins = (
            VisitCheckIn.objects.filter(
                content_type=content_type.id, object_id=self.object.id
            )
            .annotate(latest_checkin_status=Subquery(latest_checkin_status_subquery))
            .values("user", "latest_checkin_status")
            .distinct()
        )

        to_visit_count = sum(
            1 for item in latest_checkins if item["latest_checkin_status"] == "to_visit"
        )
        visiting_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["visiting", "revisiting"]
        )
        visited_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["visited", "revisited"]
        )

        # Add status counts to context
        context.update(
            {
                "to_visit_count": to_visit_count,
                "visiting_count": visiting_count,
                "visited_count": visited_count,
                "checkins": checkins,
            }
        )

        return context

    def get_level_label(self, level):
        if level == Location.LEVEL0:
            return "Continent"
        elif level == Location.LEVEL1:
            return "Polities / Sovereign Entities"
        elif level == Location.LEVEL2:
            return "Regions / States / Provinces / Cantons / Prefectures"
        elif level == Location.LEVEL3:
            return "Cities / Municipalities / Counties"
        elif level == Location.LEVEL4:
            return "Towns / Townships"
        elif level == Location.LEVEL5:
            return "Villages / Hamlets"
        elif level == Location.LEVEL6:
            return "Districts / Boroughs / Wards / Neighborhoods"
        elif level == Location.LEVEL7:
            return "Points of Interest"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        content_type = ContentType.objects.get_for_model(Movie)
        form = VisitCheckInForm(
            data=request.POST,
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": request.user.id,
                "comments_enabled": True,
            },
        )
        if form.is_valid():
            visit_check_in = form.save(commit=False)
            visit_check_in.user = request.user  # Set the user manually here
            visit_check_in.save()
        else:
            print(form.errors)

        return redirect(self.object.get_absolute_url())


class LocationUpdateView(UpdateView):
    model = Location
    form_class = LocationForm
    template_name = "visit/location_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("visit:location_detail", kwargs={"pk": self.object.pk})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["other_names"].widget = forms.TextInput()
        form.fields["address"].widget = forms.TextInput()
        return form

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class LocationListView(ListView):
    model = Location
    template_name = "location_list.html"
    context_object_name = "locations"

    def get_queryset(self):
        return (
            Location.objects.filter(level=Location.LEVEL0, historical=False)
            .prefetch_related("children")
            .order_by("name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nested_locations"] = self._get_child_locations_dict()
        return context

    def _get_child_locations_dict(self):
        locations = (
            Location.objects.filter(historical=False)
            .order_by("level", "name")
            .select_related("parent")
        )
        location_tree = defaultdict(dict)

        for loc in locations:
            location_tree[loc.parent_id][loc] = {
                "depth": int(loc.level[5:]),  # Adjust as needed
            }

        return self._build_location_hierarchy(location_tree)

    def _build_location_hierarchy(self, location_tree, parent_id=None):
        result = {}
        for loc, details in location_tree[parent_id].items():
            children = self._build_location_hierarchy(location_tree, parent_id=loc.id)
            result[loc] = {**details, "children": children}
        return result


class LocationAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Location.objects.all()

        if self.q:
            qs = qs.filter(
                Q(name__icontains=self.q) | Q(other_names__icontains=self.q)
            ).distinct()

            return qs

        return Location.objects.none()


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class LocationHistoryView(HistoryViewMixin, DetailView):
    model = Location
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_object()
        context["history_data"] = self.get_history_data(company)
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class VisitCheckInDetailView(DetailView):
    model = VisitCheckIn
    template_name = "visit/visit_checkin_detail.html"
    context_object_name = "checkin"  # This name will be used in your template

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
                content_type="VisitCheckIn",
            )
        return HttpResponseRedirect(request.path_info)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = get_visible_comments(self.request.user, self.object)
        context["comment_form"] = CommentForm()
        context["repost_form"] = RepostForm(user=self.request.user)
        context["app_label"] = self.object._meta.app_label
        context["object_type"] = self.object._meta.model_name.lower()

        checkin_count = VisitCheckIn.objects.filter(
            user=self.object.user,
            content_type=ContentType.objects.get_for_model(self.object.content_object),
            object_id=self.object.content_object.id,
        ).count()
        context["checkin_count"] = checkin_count - 1

        # Determine if the user has upvoted this ReadCheckIn object
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


class VisitCheckInUpdateView(LoginRequiredMixin, UpdateView):
    model = VisitCheckIn
    form_class = VisitCheckInForm
    template_name = "visit/visit_checkin_update.html"

    def get_success_url(self):
        return reverse_lazy(
            "write:visit_checkin_detail",
            kwargs={"pk": self.object.pk, "username": self.object.user.username},
        )


class VisitCheckInDeleteView(LoginRequiredMixin, DeleteView):
    model = VisitCheckIn
    template_name = "visit/visit_checkin_delete.html"

    def get_success_url(self):
        return reverse_lazy(
            "visit:location_detail", kwargs={"pk": self.object.content_object.pk}
        )


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class VisitCheckInListView(ListView):
    model = VisitCheckIn
    template_name = "visit/visit_checkin_list.html"
    context_object_name = "checkins"

    def get_model(self):
        if self.kwargs["model_name"] == "location":
            return Location
        else:
            return None

    def get_queryset(self):
        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        status = self.request.GET.get("status")  # Get status from query params
        profile_user = get_object_or_404(
            User, username=self.kwargs["username"]
        )  # Get user from url param
        model = self.get_model()
        if model is None:
            checkins = VisitCheckIn.objects.none()
        else:
            content_type = ContentType.objects.get_for_model(model)
            object_id = self.kwargs["object_id"]  # Get object id from url param
            checkins = VisitCheckIn.objects.filter(
                user=profile_user, content_type=content_type, object_id=object_id
            )

        # if status is specified, filter by status
        if status:
            if status == "visited_revisited":
                checkins = checkins.filter(Q(status="visited") | Q(status="revisited"))
            elif status == "visiting_revisiting":
                checkins = checkins.filter(
                    Q(status="visiting") | Q(status="revisiting")
                )
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
        if model is None:
            context["checkins"] = checkins = VisitCheckIn.objects.none()
            context["object"] = None
        else:
            content_type = ContentType.objects.get_for_model(model)
            object_id = self.kwargs["object_id"]
            checkins = self.get_queryset()

        context["object"] = model.objects.get(pk=object_id)

        # if status is specified, filter by status
        if status:
            if status == "visited_revisited":
                checkins = checkins.filter(Q(status="visited") | Q(status="revisited"))
            elif status == "visiting_revisiting":
                checkins = checkins.filter(
                    Q(status="visiting") | Q(status="revisiting")
                )
            else:
                checkins = checkins.filter(status=status)

        context["checkins"] = checkins.order_by(order)

        location = get_object_or_404(Location, pk=self.kwargs["object_id"])

        # Get the location details
        context["location"] = location

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
class VisitCheckInAllListView(ListView):
    model = VisitCheckIn
    template_name = "visit/visit_checkin_list_all.html"
    context_object_name = "checkins"
    paginate_by = 25

    def get_queryset(self):
        # Fetch the latest check-in from each user.
        content_type = ContentType.objects.get_for_model(Location)
        object_id = self.kwargs["object_id"]
        latest_checkin_subquery = (
            get_visible_checkins(
                self.request.user, VisitCheckIn, content_type, object_id
            )
            .filter(user=OuterRef("user"))
            .order_by("-timestamp")
        )

        checkins = (
            get_visible_checkins(
                self.request.user, VisitCheckIn, content_type, object_id
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

        status = self.request.GET.get("status", "")
        if status:
            if status == "visited_revisited":
                checkins = checkins.filter(Q(status="visited") | Q(status="revisited"))
            elif status == "visiting_revisiting":
                checkins = checkins.filter(
                    Q(status="visiting") | Q(status="revisiting")
                )
            else:
                checkins = checkins.filter(status=status)

        # Get the count of check-ins for each user for this game
        user_checkin_counts = (
            get_visible_checkins(
                self.request.user, VisitCheckIn, content_type, object_id
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
        # Call the base implementation first to get the context
        context = super().get_context_data(**kwargs)
        location = get_object_or_404(Location, pk=self.kwargs["object_id"])
        # Get the location details
        context["location"] = location
        context["order"] = self.request.GET.get("order", "-timestamp")

        include_mathjax, include_mermaid = check_required_js(context["page_obj"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        return context


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class VisitCheckInUserListView(ListView):
    """
    All latest check-ins from a given user of all locations.
    """

    model = VisitCheckIn
    template_name = "visit/visit_checkin_list_user.html"
    context_object_name = "checkins"
    paginate_by = 25

    def get_queryset(self):
        profile_user = get_object_or_404(User, username=self.kwargs["username"])

        latest_checkin_subquery = get_visible_checkins(
            self.request.user,
            VisitCheckIn,
            OuterRef("content_type"),
            OuterRef("object_id"),
            checkin_user=profile_user,
        ).order_by("-timestamp")

        checkins = (
            VisitCheckIn.objects.filter(user=profile_user)
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
            if status == "visited_revisited":
                checkins = checkins.filter(Q(status="visited") | Q(status="revisited"))
            elif status == "visiting_revisiting":
                checkins = checkins.filter(
                    Q(status="visiting") | Q(status="revisiting")
                )
            else:
                checkins = checkins.filter(status=status)

        # Count the check-ins for each game for this user
        user_checkin_counts = (
            VisitCheckIn.objects.filter(user=profile_user)
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
