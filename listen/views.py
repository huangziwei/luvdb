from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any

import feedparser
import requests
from dal import autocomplete
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import DatabaseError, connection, connections, transaction
from django.db.models import Count, F, Max, OuterRef, Q, Subquery
from django.db.models.functions import Length
from django.db.utils import OperationalError
from django.forms import inlineformset_factory
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    View,
)
from django_ratelimit.decorators import ratelimit
from PIL import Image

from activity_feed.models import Block
from discover.utils import user_has_upvoted
from entity.models import Creator, Role
from entity.utils import get_company_name, parse_date
from entity.views import HistoryViewMixin, get_contributors
from scrape.wikipedia import scrape_release
from write.forms import CommentForm, RepostForm
from write.models import Comment, ContentInList
from write.utils import get_visible_checkins, get_visible_comments
from write.utils_bluesky import create_bluesky_post
from write.utils_formatting import check_required_js
from write.utils_mastodon import create_mastodon_post

from .forms import (
    AudiobookForm,
    AudiobookInstanceFormSet,
    AudiobookRoleFormSet,
    ListenCheckInForm,
    ReleaseForm,
    ReleaseGroupForm,
    ReleaseInGroupFormSet,
    ReleaseRole,
    ReleaseRoleForm,
    ReleaseRoleFormSet,
    ReleaseTrack,
    ReleaseTrackForm,
    ReleaseTrackFormSet,
    TrackForm,
    TrackRole,
    TrackRoleForm,
    TrackRoleFormSet,
    WorkForm,
    WorkRoleFormSet,
)
from .models import (
    Audiobook,
    Genre,
    ListenCheckIn,
    Podcast,
    Release,
    ReleaseGroup,
    ReleaseInGroup,
    Track,
    Work,
)

User = get_user_model()


class LazyCategoriesDict:
    def __init__(self):
        self._categories = None

    @property
    def categories(self):
        if self._categories is None:
            self._categories = self.generate_categories_dict()
        return self._categories

    def generate_categories_dict(self):
        try:
            # Attempt to fetch a connection and call a simple operation to check readiness
            connections["default"].cursor()
        except (OperationalError, DatabaseError):
            # Handle the case where the database is unavailable or unready
            print("Database is unavailable or unready at the moment.")
            return {}

        from entity.models import Role  # Import here to avoid premature imports

        try:
            roles = Role.objects.filter(domain="listen")
            categories = defaultdict(list)
            for role in roles:
                if role.category:
                    categories[role.category].append(role.name)
            return dict(categories)
        except Exception as e:
            print("Failed to generate categories:", e)
            return {}


# Create a global instance of the lazy loader
CATEGORIES_LOADER = LazyCategoriesDict()

# CATEGORIES = {
#     "Performing Artists": [
#         "Singer",
#         "Guitar",
#         "Electric Guitar",
#         "Bass Guitar",
#         "Drummer",
#         "Alto Saxophone",
#         "Choir",
#         "Clarinet",
#         "Conductor",
#         "Double-bass",
#         "Flautist",
#         "Harpist",
#         "Pianist",
#         "Piano"
#         "Saxophone",
#         "Trombone",
#         "Trumpet",
#         "Violinist",
#         "Vocals",
#         "Ensemble",
#         "Performer",
#     ],
#     "Composition and Lyrics": ["Composer", "Lyricist", "Arranger", "Songwriter"],
#     "Production and Engineering": [
#         "Producer",
#         "Recording Engineer",
#         "Mixing Engineer",
#         "Mastering Engineer",
#     ],
# }

##########
## Work ##
##########


class WorkCreateView(LoginRequiredMixin, CreateView):
    model = Work
    form_class = WorkForm
    template_name = "listen/work_create.html"

    def get_success_url(self):
        return reverse_lazy("listen:work_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["workroles"] = WorkRoleFormSet(self.request.POST, instance=self.object)
        else:
            data["workroles"] = WorkRoleFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        workroles = context["workroles"]

        # Manually check validity of each form in the formset.
        if not all(workrole_form.is_valid() for workrole_form in workroles):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if workroles.is_valid():
                workroles.instance = self.object
                workroles.save()
            else:
                print(workroles.errors)  # print out formset errors
        return super().form_valid(form)


class WorkUpdateView(LoginRequiredMixin, UpdateView):
    model = Work
    form_class = WorkForm
    template_name = "listen/work_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["workroles"] = WorkRoleFormSet(self.request.POST, instance=self.object)
        else:
            data["workroles"] = WorkRoleFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        workroles = context["workroles"]

        # Manually check validity of each form in the formset.
        if not all(workrole_form.is_valid() for workrole_form in workroles):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if workroles.is_valid():
                workroles.instance = self.object
                workroles.save()
            else:
                print(workroles.errors)  # print out formset errors
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("listen:work_detail", kwargs={"pk": self.object.pk})


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class WorkDetailView(DetailView):
    model = Work
    template_name = "listen/work_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        work = get_object_or_404(Work, pk=self.kwargs.get("pk"))
        # roles
        grouped_roles = {}
        for role in work.workrole_set.all():
            if role.role.name not in grouped_roles:
                grouped_roles[role.role.name] = []
            alt_name_or_creator_name = role.alt_name or role.creator.name
            grouped_roles[role.role.name].append(
                (role.creator, alt_name_or_creator_name)
            )
        context["grouped_roles"] = grouped_roles

        # Group roles by categories
        categorized_roles = defaultdict(dict)
        for role in work.workrole_set.all():
            role_name = role.role.name
            category = next(
                (
                    cat
                    for cat, roles in CATEGORIES_LOADER.categories.items()
                    if role_name in roles
                ),
                "Other",
            )

            if role_name not in categorized_roles[category]:
                categorized_roles[category][role_name] = []

            alt_name_or_creator_name = role.alt_name or role.creator.name
            categorized_roles[category][role_name].append(
                (role.creator, alt_name_or_creator_name)
            )

        context["categorized_roles"] = dict(categorized_roles)

        # tracks
        tracks = work.tracks.all().order_by("release_date")
        context["tracks"] = []
        for track in tracks:
            releases = track.releases.all()
            for release in releases:
                release.type = "release"
            items = sorted(list(releases), key=lambda x: x.release_date)
            singers = track.creators.filter(trackrole__role__name="Singer")
            for singer in singers:
                singer.alt_name = TrackRole.objects.get(
                    track=track, creator=singer, role__name="Singer"
                ).alt_name
            context["tracks"].append(
                {"track": track, "items": items, "singers": singers}
            )

        # contributors
        context["contributors"] = get_contributors(self.object)

        return context


class WorkAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Work.objects.none()

        qs = Work.objects.all()

        if self.q:
            # get all the authors whose name starts with query
            creators = Creator.objects.filter(name__icontains=self.q)

            # get the author role
            singer_role = Role.objects.filter(name="Singer").first()

            # get all the works which are associated with these authors
            qs = qs.filter(
                Q(workrole__role=singer_role, workrole__creator__in=creators)
                | Q(title__icontains=self.q)
                | Q(other_titles__icontains=self.q)
                | Q(release_date__icontains=self.q)
            ).distinct()

            return qs

        return Work.objects.none()  # If no query is provided, return no objects

    def get_result_label(self, item):
        # Get the first creator with a role of 'Singer' for the release
        singer_role = Role.objects.filter(
            name="Singer"
        ).first()  # Adjust 'Singer' to match your data
        composer_role = Role.objects.filter(name="Composer").first()
        performer_role = Role.objects.filter(name="Performer").first()

        singer_work_role = item.workrole_set.filter(role=singer_role).first()
        composer_work_role = item.workrole_set.filter(role=composer_role).first()
        performer_work_role = item.workrole_set.filter(role=performer_role).first()
        if singer_work_role:
            creator_name = singer_work_role.creator.name
        elif composer_work_role:
            creator_name = composer_work_role.creator.name
        elif performer_work_role:
            creator_name = performer_work_role.creator.name
        else:
            creator_name = "Unknown"

        # Get the year from the release_date
        publication_year = item.release_date[:4] if item.release_date else "Unknown"

        # Format the label
        label = "{} ({}, {})".format(item.title, creator_name, publication_year)

        return mark_safe(label)


###########
## Track ##
###########


class TrackCreateView(LoginRequiredMixin, CreateView):
    model = Track
    form_class = TrackForm
    template_name = "listen/track_create.html"

    def get_success_url(self):
        return reverse_lazy("listen:track_detail", kwargs={"pk": self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        work_id = self.kwargs.get("work_id")  # Attempt to get 'work_id' from URL

        if not work_id and "work_id" in self.request.session:
            # Fallback to session if 'work_id' is not in URL
            work_id = self.request.session["work_id"]

        if work_id:
            work = get_object_or_404(Work, id=work_id)
            # Prefill form fields based on the Work
            initial.update(
                {
                    "work": work,
                    "title": work.title,
                    "other_titles": work.other_titles,
                    "release_date": work.release_date,
                    "recorded_date": work.recorded_date,
                    "wikipedia": work.wikipedia,
                    "genres": work.genres.all(),
                }
            )

        return initial

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        work_id = self.kwargs.get("work_id") or self.request.session.get("work_id")

        if self.request.POST:
            data["trackroles"] = TrackRoleFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["trackroles"] = TrackRoleFormSet(instance=self.object)
            if work_id:
                work = get_object_or_404(Work, id=work_id)
                work_roles = work.workrole_set.all()

                initial_roles = [
                    {
                        "creator": role.creator.id,
                        "role": role.role.id,
                        "alt_name": role.alt_name,
                        "domain": "listen",  # Assuming 'listen' is the correct domain for tracks
                    }
                    for role in work_roles
                ]
                num_initial_roles = len(initial_roles) if len(initial_roles) > 0 else 1

                # Adjust the formset based on the number of roles when work is provided
                TrackRoleFormSet_prefilled = inlineformset_factory(
                    Track,
                    TrackRole,
                    form=TrackRoleForm,
                    extra=num_initial_roles,
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
                            forward=[
                                "domain"
                            ],  # forward the domain field to the RoleAutocomplete view
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

                data["trackroles"] = TrackRoleFormSet_prefilled(
                    instance=self.object,
                    initial=initial_roles,
                    queryset=TrackRole.objects.none(),
                )

        return data

    def form_valid(self, form):
        context = self.get_context_data()
        trackroles = context["trackroles"]

        # Manually check validity of each form in the formset.
        if not all(trackrole_form.is_valid() for trackrole_form in trackroles):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if trackroles.is_valid():
                trackroles.instance = self.object
                trackroles.save()
            else:
                print(trackroles.errors)  # print out formset errors
        return super().form_valid(form)


class TrackUpdateView(LoginRequiredMixin, UpdateView):
    model = Track
    form_class = TrackForm
    template_name = "listen/track_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["trackroles"] = TrackRoleFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["trackroles"] = TrackRoleFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        trackroles = context["trackroles"]

        # Manually check validity of each form in the formset.
        if not all(trackrole_form.is_valid() for trackrole_form in trackroles):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if trackroles.is_valid():
                trackroles.instance = self.object
                trackroles.save()
            else:
                print(trackroles.errors)  # print out formset errors
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("listen:track_detail", kwargs={"pk": self.object.pk})


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class TrackDetailView(DetailView):
    model = Track
    template_name = "listen/track_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        track = get_object_or_404(Track, pk=self.kwargs.get("pk"))

        # Group roles by categories
        categorized_roles = defaultdict(dict)
        for role in track.trackrole_set.all():
            role_name = role.role.name
            category = next(
                (
                    cat
                    for cat, roles in CATEGORIES_LOADER.categories.items()
                    if role_name in roles
                ),
                "Other",
            )

            if role_name not in categorized_roles[category]:
                categorized_roles[category][role_name] = []

            alt_name_or_creator_name = role.alt_name or role.creator.name
            categorized_roles[category][role_name].append(
                (role.creator, alt_name_or_creator_name)
            )

        context["categorized_roles"] = dict(categorized_roles)

        context["releases"] = track.releases.all().order_by("release_date")

        # contributors
        context["contributors"] = get_contributors(self.object)

        # Track Check-ins
        track_check_ins = []
        for release_track in ReleaseTrack.objects.filter(track=track):
            disk_order_pattern = f"{release_track.disk}.{release_track.order}"
            check_ins_for_track = ListenCheckIn.objects.filter(
                content_type=ContentType.objects.get_for_model(Release),
                object_id=release_track.release.id,
                progress=disk_order_pattern,
                progress_type="TR",
            )
            track_check_ins.extend(check_ins_for_track)

        track_check_ins.sort(key=lambda x: x.timestamp, reverse=True)
        context["track_checkins"] = track_check_ins
        return context


class TrackAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Track.objects.none()

        qs = Track.objects.all()

        if self.q:
            # get all the authors whose name starts with query
            creators = Creator.objects.filter(name__icontains=self.q)

            # get the author role
            singer_role = Role.objects.filter(name__in=["Performer", "Singer"]).first()

            # get all the instances which are associated with these authors
            qs = qs.filter(
                Q(trackrole__role=singer_role, trackrole__creator__in=creators)
                | Q(title__icontains=self.q)
                | Q(other_titles__icontains=self.q)
                | Q(release_date__icontains=self.q)
            ).distinct()

            return qs

        return Track.objects.none()  # If no query is provided, return no objects

    def get_result_label(self, item):
        # Get the role objects for 'Singer' and 'Composer'
        singer_role = Role.objects.filter(name="Singer").first()
        composer_role = Role.objects.filter(name="Composer").first()
        performer_role = Role.objects.filter(name="Performer").first()

        # Fetch the track_role for 'Singer' and 'Composer'
        singer_track_role = item.trackrole_set.filter(role=singer_role).first()
        composer_track_role = item.trackrole_set.filter(role=composer_role).first()
        performer_track_role = item.trackrole_set.filter(role=performer_role).first()

        # Check if singer_track_role exists and a creator is associated
        if singer_track_role:
            creator_name = (
                singer_track_role.alt_name
                if singer_track_role.alt_name
                else singer_track_role.creator.name
            )
        # If no singer, use performer
        elif performer_track_role:
            creator_name = (
                performer_track_role.alt_name
                if performer_track_role.alt_name
                else performer_track_role.creator.name
            )
        # If no perfomer, use composer
        elif composer_track_role:
            creator_name = (
                composer_track_role.alt_name
                if composer_track_role.alt_name
                else composer_track_role.creator.name
            )
        else:
            creator_name = "Unknown"

        # Get the year from the release_date
        release_year = item.release_date[:4] if item.release_date else "Unknown"

        # Format the label
        label = "{} ({}, {})".format(item.title, creator_name, release_year)

        return mark_safe(label)


###########
# Release #
###########


class ReleaseCreateView(LoginRequiredMixin, CreateView):
    model = Release
    form_class = ReleaseForm
    template_name = "listen/release_create.html"

    def get_success_url(self):
        return reverse_lazy("listen:release_detail", kwargs={"pk": self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        track_id = self.kwargs.get("track_id")  # Attempt to get 'track_id' from URL

        if not track_id and "track_id" in self.request.session:
            # Fallback to session if 'track_id' is not in URL
            track_id = self.request.session["track_id"]

        if track_id:
            track = get_object_or_404(Track, id=track_id)
            # Prefill form fields based on the Track
            initial.update(
                {
                    "title": track.title,
                    "other_titles": track.other_titles,
                    "release_date": track.release_date,
                    "recorded_date": track.recorded_date,
                    "wikipedia": track.wikipedia,
                    "release_length": track.length,
                    "release_type": "Single",
                    "wikipedia": track.wikipedia,
                }
            )
        return initial

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        track_id = self.kwargs.get("track_id") or self.request.session.get("track_id")
        if self.request.POST:
            data["releaseroles"] = ReleaseRoleFormSet(
                self.request.POST, instance=self.object
            )
            data["releasetracks"] = ReleaseTrackFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["releaseroles"] = ReleaseRoleFormSet(instance=self.object)
            data["releasetracks"] = ReleaseTrackFormSet(instance=self.object)

            if track_id:
                track = get_object_or_404(Track, id=track_id)
                track_roles = track.trackrole_set.all()

                initial_roles = [
                    {
                        "creator": role.creator.id,
                        "role": role.role.id,
                        "alt_name": role.alt_name,
                        "domain": "listen",  # Assuming 'listen' is the correct domain for releases
                    }
                    for role in track_roles
                ]
                num_initial_roles = len(initial_roles) if len(initial_roles) > 0 else 1
                ReleaseRoleFormSet_prefilled = inlineformset_factory(
                    Release,
                    ReleaseRole,
                    form=ReleaseRoleForm,
                    extra=num_initial_roles,
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
                            forward=[
                                "domain"
                            ],  # forward the domain field to the RoleAutocomplete view
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

                data["releaseroles"] = ReleaseRoleFormSet_prefilled(
                    instance=self.object,
                    initial=initial_roles,
                    queryset=ReleaseRole.objects.none(),
                )

                initial_tracks = [
                    {
                        "track": track,
                        "disk": 1,
                        "order": 1,
                    }
                ]

                num_initial_tracks = (
                    len(initial_tracks) if len(initial_tracks) > 0 else 1
                )
                ReleaseTrackFormSet_prefilled = inlineformset_factory(
                    Release,
                    ReleaseTrack,
                    form=ReleaseTrackForm,
                    extra=num_initial_tracks,
                    can_delete=True,
                    widgets={
                        "track": autocomplete.ModelSelect2(
                            url=reverse_lazy("listen:track-autocomplete")
                        ),
                    },
                )

                data["releasetracks"] = ReleaseTrackFormSet_prefilled(
                    instance=self.object,
                    initial=initial_tracks,
                    queryset=ReleaseTrack.objects.none(),
                )

        return data

    def form_valid(self, form):
        context = self.get_context_data()
        releaseroles = context["releaseroles"]
        releasetracks = context["releasetracks"]

        # Manually check validity of each form in the formset.
        if not all(releaserole_form.is_valid() for releaserole_form in releaseroles):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if releaseroles.is_valid():
                releaseroles.instance = self.object
                releaseroles.save()
            if releasetracks.is_valid():
                releasetracks.instance = self.object
                releasetracks.save()
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        if "wiki_url" in request.POST:
            wiki_url = request.POST.get("wiki_url")
            scraped_data = scrape_release(wiki_url)
            if scraped_data:
                # Initialize the form with imported data
                form = self.form_class(initial=scraped_data)
                # Initialize formsets without relying on self.object
                releaseroles = ReleaseRoleFormSet()
                releasetracks = ReleaseTrackFormSet()

                # Render response with initialized form and formsets
                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                        "releaseroles": releaseroles,
                        "releasetracks": releasetracks,
                    },
                )
            else:
                # Handle case where import fails
                return self.form_invalid(form)
        else:
            return super().post(request, *args, **kwargs)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class ReleaseDetailView(DetailView):
    model = Release
    template_name = "listen/release_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        release = get_object_or_404(Release, pk=self.kwargs["pk"])
        context["content_type"] = "release"

        main_role_names = ["Performer", "Conductor", "Compiler"]
        main_roles = {}
        other_roles = {}

        for release_role in release.releaserole_set.all():
            role_name = release_role.role.name
            alt_name_or_creator_name = (
                release_role.alt_name or release_role.creator.name
            )

            if role_name in main_role_names:
                if role_name not in main_roles:
                    main_roles[role_name] = []
                main_roles[role_name].append(
                    (release_role.creator, alt_name_or_creator_name)
                )
            else:
                if role_name not in other_roles:
                    other_roles[role_name] = []
                other_roles[role_name].append(
                    (release_role.creator, alt_name_or_creator_name)
                )

        context["main_roles"] = main_roles
        context["other_roles"] = other_roles

        content_type = ContentType.objects.get_for_model(Release)
        context["checkin_form"] = ListenCheckInForm(
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": self.request.user.id,
            }
        )

        # Fetch the latest check-in from each user.
        latest_checkin_subquery = (
            get_visible_checkins(
                self.request.user, ListenCheckIn, content_type, self.object.id
            )
            .filter(user=OuterRef("user"))
            .order_by("-timestamp")
        )
        checkins = (
            get_visible_checkins(
                self.request.user, ListenCheckIn, content_type, self.object.id
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
                self.request.user, ListenCheckIn, content_type, self.object.id
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

        # Release check-in status counts, considering only latest check-in per user
        latest_checkin_status_subquery = (
            get_visible_checkins(
                self.request.user,
                ListenCheckIn,
                content_type,
                self.object.id,
                checkin_user=OuterRef("user"),
            )
            .order_by("-timestamp")
            .values("status")[:1]
        )
        latest_checkins = (
            ListenCheckIn.objects.filter(
                content_type=content_type.id, object_id=self.object.id
            )
            .annotate(latest_checkin_status=Subquery(latest_checkin_status_subquery))
            .values("user", "latest_checkin_status")
            .distinct()
        )

        to_listen_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] == "to_listen"
        )
        listening_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["looping", "relistening"]
        )
        listened_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["listened", "relistened"]
        )

        # Add status counts to context
        context.update(
            {
                "to_listen_count": to_listen_count,
                "listening_count": listening_count,
                "listened_count": listened_count,
            }
        )

        # Get the ContentType for the Issue model
        release_content_type = ContentType.objects.get_for_model(Release)

        # Query ContentInList instances that have the release as their content_object
        lists_containing_release = ContentInList.objects.filter(
            content_type=release_content_type, object_id=self.object.id
        ).order_by("luv_list__title")

        context["lists_containing_release"] = lists_containing_release

        # Fetch the latest check-in from the current user for this book
        if self.request.user.is_authenticated:
            latest_user_checkin = (
                ListenCheckIn.objects.filter(
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
                context["latest_user_status"] = "to_listen"
        else:
            context["latest_user_status"] = "to_listen"

        # contributors
        context["contributors"] = get_contributors(self.object)

        # check required js
        include_mathjax, include_mermaid = check_required_js(context["checkins"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        context["genres"] = self.object.get_genres()

        context["labels"] = get_company_name(release.label.all(), release.release_date)

        context["has_voted"] = user_has_upvoted(self.request.user, self.object)
        context["can_vote"] = (
            self.request.user.is_authenticated
            and ListenCheckIn.objects.filter(
                content_type=ContentType.objects.get_for_model(Release),
                object_id=self.object.id,
                user=self.request.user,
                status__in=["listened", "relistened"],
            ).exists()
        )

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        content_type = ContentType.objects.get_for_model(Release)
        form = ListenCheckInForm(
            data=request.POST,
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": request.user.id,
            },
        )
        if form.is_valid():
            release_check_in = form.save(commit=False)
            release_check_in.user = request.user  # Set the user manually here
            release_check_in.save()
        else:
            print("listen_checkin_in_detail:", form.errors)

        return redirect(self.object.get_absolute_url())


class ReleaseUpdateView(LoginRequiredMixin, UpdateView):
    model = Release
    form_class = ReleaseForm
    template_name = "listen/release_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("listen:release_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["releaseroles"] = ReleaseRoleFormSet(
                self.request.POST, instance=self.object
            )
            data["releasetracks"] = ReleaseTrackFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["releaseroles"] = ReleaseRoleFormSet(instance=self.object)
            data["releasetracks"] = ReleaseTrackFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        releaseroles = context["releaseroles"]
        releasetracks = context["releasetracks"]

        # Manually check validity of each form in the formset.
        if not all(releaserole_form.is_valid() for releaserole_form in releaseroles):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.updated_by = self.request.user
            if self.request.method == "POST":
                form = ReleaseForm(
                    self.request.POST, self.request.FILES, instance=self.object
                )
                if form.is_valid():
                    self.object = form.save()
                    if releaseroles.is_valid():
                        releaseroles.instance = self.object
                        releaseroles.save()
                    else:
                        print(
                            "ReleaseRoles form errors: ", releaseroles.errors
                        )  # print form errors
                    if releasetracks.is_valid():
                        releasetracks.instance = self.object
                        releasetracks.save()

        return super().form_valid(form)


class ReleaseAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Release.objects.none()

        qs = Release.objects.all()

        if self.q:
            # get all the authors whose name starts with query
            creators = Creator.objects.filter(name__icontains=self.q)

            # get the author role
            performer_role = Role.objects.filter(name="Performer").first()

            # get all the instances which are associated with these authors
            qs = qs.filter(
                Q(releaserole__role=performer_role, releaserole__creator__in=creators)
                | Q(title__icontains=self.q)
                | Q(other_titles__icontains=self.q)
                | Q(release_date__icontains=self.q)
            ).distinct()

            return qs

        return Release.objects.none()  # If no query is provided, return no objects

    def get_result_label(self, item):
        # Get the role objects for 'Performer'
        performer_role = Role.objects.filter(name="Performer").first()

        # Fetch the release_role for 'Performer'
        performer_release_role = item.releaserole_set.filter(
            role=performer_role
        ).first()

        # Check if performer_release_role exists and a creator is associated
        if performer_release_role:
            creator_name = (
                performer_release_role.alt_name
                if performer_release_role.alt_name
                else performer_release_role.creator.name
            )
        else:
            creator_name = "Unknown"

        # Get the year from the release_date
        release_year = item.release_date[:4] if item.release_date else "Unknown"

        # Format the label
        label = "{} ({}, {})".format(item.title, creator_name, release_year)

        return mark_safe(label)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class ReleaseCreditDetailView(DetailView):
    model = Release
    template_name = "listen/credit_detail.html"
    context_object_name = "release"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the Release object
        release = self.get_object()

        # Aggregate Release level credits
        def categorize_roles(roles, categories):
            categorized_roles = defaultdict(dict)
            for role in roles:
                role_name = role.role.name
                category = next(
                    (cat for cat, roles in categories.items() if role_name in roles),
                    "Other",
                )

                if role_name not in categorized_roles[category]:
                    categorized_roles[category][role_name] = []

                alt_name_or_creator_name = role.alt_name or role.creator.name
                categorized_roles[category][role_name].append(
                    (role.creator, alt_name_or_creator_name)
                )
            return dict(categorized_roles)

        # Aggregate and categorize Release level credits
        release_roles = ReleaseRole.objects.filter(release=release)
        categorized_release_credits = categorize_roles(
            release_roles, CATEGORIES_LOADER.categories
        )

        # Aggregate and categorize Track level credits
        release_tracks = ReleaseTrack.objects.filter(release=release).order_by(
            "disk", "order"
        )
        categorized_track_credits = {}

        for release_track in release_tracks:
            disk = release_track.disk
            order = release_track.order

            track_roles = TrackRole.objects.filter(track=release_track.track)
            categorized_track_credits[(release_track.track, disk, order)] = (
                categorize_roles(track_roles, CATEGORIES_LOADER.categories)
            )

        context["categorized_release_credits"] = categorized_release_credits
        context["categorized_track_credits"] = categorized_track_credits

        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class ListenCheckInDetailView(DetailView):
    model = ListenCheckIn
    template_name = "listen/listen_checkin_detail.html"
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
                content_type="ListenCheckIn",
            )
        return HttpResponseRedirect(request.path_info)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = get_visible_comments(self.request.user, self.object)
        context["comment_form"] = CommentForm()
        context["repost_form"] = RepostForm(user=self.request.user)
        context["app_label"] = self.object._meta.app_label
        context["object_type"] = self.object._meta.model_name.lower()

        checkin_count = ListenCheckIn.objects.filter(
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

        # check required js
        include_mathjax, include_mermaid = check_required_js([self.object])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid
        context["source_url"] = self.request.build_absolute_uri()
        return context


class ListenCheckInUpdateView(LoginRequiredMixin, UpdateView):
    model = ListenCheckIn
    form_class = ListenCheckInForm
    template_name = "listen/listen_checkin_update.html"

    def get_success_url(self):
        return reverse_lazy(
            "write:listen_checkin_detail",
            kwargs={"pk": self.object.pk, "username": self.object.user.username},
        )


class ListenCheckInDeleteView(LoginRequiredMixin, DeleteView):
    model = ListenCheckIn
    template_name = "listen/listen_checkin_delete.html"

    def get_success_url(self):
        if self.object.content_type.model == "release":
            return reverse_lazy(
                "listen:release_detail", kwargs={"pk": self.object.content_object.pk}
            )
        elif self.object.content_type.model == "podcast":
            return reverse_lazy(
                "listen:podcast_detail", kwargs={"pk": self.object.content_object.pk}
            )
        elif self.object.content_type.model == "audiobook":
            return reverse_lazy(
                "listen:audiobook_detail", kwargs={"pk": self.object.content_object.pk}
            )


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class ListenListView(ListView):
    template_name = "listen/listen_list.html"
    context_object_name = "objects"

    def get_queryset(self):
        recent_releases = Release.objects.all().order_by("-created_at")[:12]
        recent_podcasts = Podcast.objects.all().order_by("-created_at")[:12]
        recent_audiobooks = Audiobook.objects.all().order_by("-created_at")[:12]
        recent_date = timezone.now() - timedelta(days=7)

        release_content_type = ContentType.objects.get_for_model(Release)
        trending_releases = (
            Release.objects.annotate(
                checkins=Count(
                    "listencheckin",
                    filter=Q(
                        listencheckin__content_type=release_content_type,
                        listencheckin__timestamp__gte=recent_date,
                    ),
                    distinct=True,
                ),
                latest_checkin=Max(
                    "listencheckin__timestamp",
                    filter=Q(
                        listencheckin__content_type=release_content_type,
                        listencheckin__timestamp__gte=recent_date,
                    ),
                ),
            )
            .exclude(checkins=0)
            .order_by("-latest_checkin")[:12]
        )
        podcast_content_type = ContentType.objects.get_for_model(Podcast)
        trending_podcasts = (
            Podcast.objects.annotate(
                checkins=Count(
                    "listencheckin",
                    filter=Q(
                        listencheckin__content_type=podcast_content_type,
                        listencheckin__timestamp__gte=recent_date,
                    ),
                    distinct=True,
                ),
                latest_checkin=Max(
                    "listencheckin__timestamp",
                    filter=Q(
                        listencheckin__content_type=podcast_content_type,
                        listencheckin__timestamp__gte=recent_date,
                    ),
                ),
            )
            .exclude(checkins=0)
            .order_by("-latest_checkin")[:12]
        )
        audiobook_content_type = ContentType.objects.get_for_model(Audiobook)
        trending_audiobooks = (
            Audiobook.objects.annotate(
                checkins=Count(
                    "listencheckin",
                    filter=Q(
                        listencheckin__content_type=audiobook_content_type,
                        listencheckin__timestamp__gte=recent_date,
                    ),
                    distinct=True,
                ),
                latest_checkin=Max(
                    "listencheckin__timestamp",
                    filter=Q(
                        listencheckin__content_type=audiobook_content_type,
                        listencheckin__timestamp__gte=recent_date,
                    ),
                ),
            )
            .exclude(checkins=0)
            .order_by("-latest_checkin")[:12]
        )

        return {
            "recent_releases": recent_releases,
            "trending_releases": trending_releases,
            "recent_podcasts": recent_podcasts,
            "trending_podcasts": trending_podcasts,
            "recent_audiobooks": recent_audiobooks,
            "trending_audiobooks": trending_audiobooks,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Include genres with at least one movie or series
        context["genres"] = (
            Genre.objects.filter(Q(listen_works__isnull=False))
            .order_by("name")
            .distinct()
        )

        context["works_count"] = Work.objects.count()
        context["tracks_count"] = Track.objects.count()
        context["releases_count"] = Release.objects.count()
        context["podcasts_count"] = Podcast.objects.count()
        context["audiobooks_count"] = Audiobook.objects.count()

        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class ListenListAllView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = "listen/listen_list_all.html"
    context_object_name = "objects"

    def test_func(self):
        # Only allow superusers
        return self.request.user.is_superuser

    def handle_no_permission(self):
        # If not allowed, raise a 404 error
        raise Http404

    def get_queryset(self):
        releases = Release.objects.all().order_by("-created_at")
        podcasts = Podcast.objects.all().order_by("-created_at")
        audiobooks = Audiobook.objects.all().order_by("-created_at")

        return {
            "releases": releases,
            "podcasts": podcasts,
            "audiobooks": audiobooks,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Include genres with at least one movie or series
        context["genres"] = (
            Genre.objects.filter(Q(listen_works__isnull=False))
            .order_by("name")
            .distinct()
        )

        context["works_count"] = Work.objects.count()
        context["tracks_count"] = Track.objects.count()
        context["releases_count"] = Release.objects.count()
        context["podcasts_count"] = Podcast.objects.count()
        context["audiobooks_count"] = Audiobook.objects.count()
        return context


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class GenericCheckInUserListView(ListView):
    """
    All latest check-ins from a given user of all audio tracks and albums.
    """

    model = ListenCheckIn
    template_name = "listen/listen_checkin_list_user.html"
    context_object_name = "checkins"
    paginate_by = 25

    def get_queryset(self):
        profile_user = get_object_or_404(User, username=self.kwargs["username"])

        latest_checkin_subquery = get_visible_checkins(
            self.request.user,
            ListenCheckIn,
            OuterRef("content_type"),
            OuterRef("object_id"),
            checkin_user=profile_user,
        ).order_by("-timestamp")

        checkins = (
            ListenCheckIn.objects.filter(user=profile_user)
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

        status = self.request.GET.get("status", "")
        if status:
            checkins = checkins.filter(status=status)

        # Adding count of check-ins for each book or issue
        user_checkin_counts = (
            ListenCheckIn.objects.filter(user=profile_user)
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

        return checkins

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        profile_user = get_object_or_404(User, username=self.kwargs["username"])
        context["profile_user"] = profile_user

        context["order"] = self.request.GET.get("order", "-timestamp")
        context["layout"] = self.request.GET.get("layout", "list")
        context["status"] = self.request.GET.get("status", "")

        # check required js
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
    template_name = "listen/genre_detail.html"  # Update with your actual template name
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the genre object
        genre = self.object
        works = Work.objects.filter(genres=genre).order_by("-release_date")

        context["works"] = works

        return context


class GenreAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Genre.objects.none()

        qs = Genre.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs.order_by("name")


###########
# Podcast #
###########


def parse_podcast(rss_feed_url):
    """
    Parse the given RSS feed URL and returns a dictionary with podcast and episodes information.
    """
    feed = feedparser.parse(rss_feed_url)

    podcast_info = {
        "title": feed.feed.title,
        "description": (
            feed.feed.description if hasattr(feed.feed, "description") else None
        ),
        "publisher": feed.feed.publisher if hasattr(feed.feed, "publisher") else None,
        "rss_feed_url": rss_feed_url,
        "website_url": feed.feed.link if hasattr(feed.feed, "link") else None,
        "cover": (
            fetch_image_from_url(feed.feed.image.href)
            if hasattr(feed.feed, "image")
            else None
        ),
    }
    podcast_info["author"] = getattr(feed.feed, "author", None)
    podcast_info["language"] = getattr(feed.feed, "language", None)
    if hasattr(feed.feed, "copyright"):
        podcast_info["copyright"] = (
            feed.feed.copyright.replace("&copy;", "").replace("©", "").strip()
        )
    else:
        podcast_info["copyright"] = None
    podcast_info["last_updated"] = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    podcast_info["categories"] = list(
        set(cat.term for cat in feed.feed.get("tags", []) if hasattr(cat, "term"))
    )
    podcast_info["explicit"] = getattr(feed.feed, "explicit", None)

    episodes_info = []
    for entry in feed.entries:
        # Convert datetime object to string representation
        release_date = (
            datetime(*entry.published_parsed[:6])
            if hasattr(entry, "published_parsed")
            else None
        )
        if release_date:
            release_date = release_date.strftime("%Y-%m-%d %H:%M:%S")

        if hasattr(entry, "link"):
            episode_url = entry.link
            episode_url_type = "web"
        elif entry.enclosures:
            episode_url = entry.enclosures[0].href
            episode_url_type = "audio"
        else:
            episode_url = None
            episode_url_type = None

        episode_info = {
            "title": entry.title,
            "release_date": release_date,
            "episode_url": episode_url,
            "episode_url_type": episode_url_type,
        }
        episodes_info.append(episode_info)

    podcast_info["episodes"] = episodes_info

    return podcast_info


def create_or_update_podcast_from_feed(rss_feed_url):
    """
    Create or update Podcast and PodcastEpisode from the given RSS feed URL.
    """
    podcast_info = parse_podcast(rss_feed_url)
    podcast, created = Podcast.objects.update_or_create(
        rss_feed_url=rss_feed_url, defaults=podcast_info
    )
    return podcast


def fetch_image_from_url(url):
    response = requests.get(url, stream=True)
    response.raise_for_status()

    # Open the image using PIL
    image = Image.open(BytesIO(response.content))

    # Save the image in memory
    img_temp = BytesIO()
    image.save(img_temp, format=image.format)

    # Convert it to a Django-compatible format
    img_name = url.split("/")[-1]  # Take the last part of the URL as the image name
    django_file = InMemoryUploadedFile(
        img_temp, None, img_name, "image/" + image.format.lower(), img_temp.tell, None
    )

    return django_file


class PodcastCreateView(View):
    template_name = "listen/podcast_create.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        rss_feed_url = request.POST.get("rss_feed_url")
        if rss_feed_url:
            try:
                podcast = create_or_update_podcast_from_feed(rss_feed_url)
                return redirect(
                    reverse("listen:podcast_detail", kwargs={"pk": podcast.pk})
                )
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
                return render(request, self.template_name)


class PodcastUpdateView(UpdateView):
    model = Podcast
    template_name = "listen/podcast_update.html"
    fields = [
        "title",
        "subtitle",
        "cover",
        "description",
        "publisher",
        "genres",
        "rss_feed_url",
        "website_url",
        "language",
        "copyright",
        "explicit",
        "author",
    ]

    def get_success_url(self):
        return reverse_lazy("listen:podcast_detail", kwargs={"pk": self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class PodcastDetailView(DetailView):
    model = Podcast
    template_name = "listen/podcast_detail.html"
    context_object_name = "podcast"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Calculate the time difference
        if self.object.last_updated:
            time_diff = timezone.now() - self.object.last_updated
            if time_diff < timedelta(days=1):
                context["recently_updated"] = True
            else:
                context["recently_updated"] = False
        else:
            context["recently_updated"] = False

        context["content_type"] = "podcast"
        # Add the check-in related context data (following the ReleaseDetailView example)
        content_type = ContentType.objects.get_for_model(Podcast)
        context["checkin_form"] = ListenCheckInForm(
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": self.request.user.id,
            }
        )

        latest_checkin_subquery = (
            get_visible_checkins(
                self.request.user, ListenCheckIn, content_type, self.object.id
            )
            .filter(user=OuterRef("user"))
            .order_by("-timestamp")
        )

        checkins = (
            get_visible_checkins(
                self.request.user, ListenCheckIn, content_type, self.object.id
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
                self.request.user, ListenCheckIn, content_type, self.object.id
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

        latest_checkin_status_subquery = (
            ListenCheckIn.objects.filter(
                content_type=content_type.id,
                object_id=self.object.id,
                user=OuterRef("user"),
            )
            .order_by("-timestamp")
            .values("status")[:1]
        )
        latest_checkins = (
            get_visible_checkins(
                self.request.user,
                ListenCheckIn,
                content_type,
                self.object.id,
                checkin_user=OuterRef("user"),
            )
            .annotate(latest_checkin_status=Subquery(latest_checkin_status_subquery))
            .values("user", "latest_checkin_status")
            .distinct()
        )

        to_listen_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] == "to_listen"
        )
        listening_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["looping", "relistening"]
        )
        listened_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["listened", "relistened"]
        )

        # Add status counts to context
        context.update(
            {
                "to_listen_count": to_listen_count,
                "listening_count": listening_count,
                "listened_count": listened_count,
            }
        )

        # Get the ContentType for the Issue model
        podcast_content_type = ContentType.objects.get_for_model(Podcast)

        # Query ContentInList instances that have the podcast as their content_object
        lists_containing_podcast = ContentInList.objects.filter(
            content_type=podcast_content_type, object_id=self.object.id
        ).order_by("luv_list__title")

        context["lists_containing_podcast"] = lists_containing_podcast

        # Fetch the latest check-in from the current user for this book
        if self.request.user.is_authenticated:
            latest_user_checkin = (
                ListenCheckIn.objects.filter(
                    content_type=content_type.id,
                    object_id=self.object.id,
                    user=self.request.user,
                )
                .order_by("-timestamp")
                .first()
            )
            if latest_user_checkin is not None:
                context["latest_user_status"] = latest_user_checkin.status
                print(latest_user_checkin.status)
            else:
                context["latest_user_status"] = "to_listen"
        else:
            context["latest_user_status"] = "to_listen"

        context["has_voted"] = user_has_upvoted(self.request.user, self.object)
        context["can_vote"] = (
            self.request.user.is_authenticated
            and ListenCheckIn.objects.filter(
                content_type=ContentType.objects.get_for_model(Podcast),
                object_id=self.object.id,
                user=self.request.user,
                status__in=["subscribed", "sampled"],
            ).exists()
        )

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.POST.get("action") == "recrawl":
            try:
                # Re-parse the podcast from its feed
                updated_podcast_info = parse_podcast(self.object.rss_feed_url)
                # Update the episodes (assuming it's a JSONField)
                for attr, value in updated_podcast_info.items():
                    if hasattr(self.object, attr):
                        setattr(self.object, attr, value)
                self.object.save()

                # Redirecting to the same detail page after update
                messages.success(request, "Podcast episodes have been updated!")
                return redirect(self.object.get_absolute_url())

            except Exception as e:
                messages.error(request, f"Failed to update the podcast: {str(e)}")
                return redirect(self.object.get_absolute_url())

        content_type = ContentType.objects.get_for_model(Podcast)
        form = ListenCheckInForm(
            data=request.POST,
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": request.user.id,
            },
        )
        if form.is_valid():
            podcast_check_in = form.save(commit=False)
            podcast_check_in.user = request.user  # Set the user manually here
            podcast_check_in.save()
        else:
            print("listen_checkin_in_detail:", form.errors)

        return redirect(self.object.get_absolute_url())


##########################
# Generic Checkins views #
##########################


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class GenericCheckInListView(ListView):
    """
    All check-ins from a given user for a release, a podcast or an audiobook.
    """

    model = ListenCheckIn
    template_name = "listen/listen_checkin_list.html"
    context_object_name = "checkins"

    def get_model(self):
        if self.kwargs["model_name"] == "release":
            return Release
        elif self.kwargs["model_name"] == "podcast":
            return Podcast
        elif self.kwargs["model_name"] == "audiobook":
            return Audiobook
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
            checkins = ListenCheckIn.objects.none()
        else:
            content_type = ContentType.objects.get_for_model(model)
            object_id = self.kwargs["object_id"]  # Get object id from url param

            checkins = ListenCheckIn.objects.filter(
                user=profile_user, content_type=content_type, object_id=object_id
            )

            if self.request.user.is_authenticated:
                checkins = checkins.filter(
                    Q(visibility="PU") | Q(visible_to=self.request.user)
                )
            else:
                checkins = checkins.filter(visibility="PU")

        if status:
            if status == "listened_relistened":
                checkins = checkins.filter(
                    Q(status="listened") | Q(status="relistened")
                )
            elif status == "listening_relistening":
                checkins = checkins.filter(
                    Q(status="listening") | Q(status="relistening")
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
            context["checkins"] = ListenCheckIn.objects.none()
            context["object"] = None
        else:
            content_type = ContentType.objects.get_for_model(model)
            object_id = self.kwargs["object_id"]  # Get object id from url param
            context["checkins"] = (
                self.get_queryset()
            )  # Use the queryset method to handle status filter
            context["object"] = model.objects.get(
                pk=object_id
            )  # Get the object details

        context["model_name"] = content_type.model

        if context["model_name"] == "release":
            release = model.objects.get(pk=object_id)  # Get the object details
            roles = {}
            for release_role in release.releaserole_set.all():
                if release_role.role.name not in roles:
                    roles[release_role.role.name] = []
                alt_name_or_creator_name = (
                    release_role.alt_name or release_role.creator.name
                )
                roles[release_role.role.name].append(
                    (release_role.creator, alt_name_or_creator_name)
                )
            context["roles"] = roles
        elif context["model_name"] == "audiobook":
            audiobook = model.objects.get(pk=object_id)  # Get the object details
            roles = {}
            for audiobook_role in audiobook.audiobookrole_set.all():
                if audiobook_role.role.name not in roles:
                    roles[audiobook_role.role.name] = []
                alt_name_or_creator_name = (
                    audiobook_role.alt_name or audiobook_role.creator.name
                )
                roles[audiobook_role.role.name].append(
                    (audiobook_role.creator, alt_name_or_creator_name)
                )
            context["roles"] = roles

        # check required js
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
    model = ListenCheckIn
    template_name = "listen/listen_checkin_list_all.html"
    context_object_name = "checkins"
    paginate_by = 25

    def get_model(self):
        if self.kwargs["model_name"] == "release":
            return Release
        elif self.kwargs["model_name"] == "podcast":
            return Podcast
        elif self.kwargs["model_name"] == "audiobook":
            return Audiobook
        else:
            return None

    def get_queryset(self):
        model = self.get_model()
        if model is None:
            return ListenCheckIn.objects.none()

        content_type = ContentType.objects.get_for_model(model)
        object_id = self.kwargs["object_id"]  # Get object id from url param

        latest_checkin_subquery = (
            get_visible_checkins(
                self.request.user, ListenCheckIn, content_type, object_id
            )
            .filter(user=OuterRef("user"))
            .order_by("-timestamp")
        )

        checkins = (
            get_visible_checkins(
                self.request.user, ListenCheckIn, content_type, object_id
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
            if status == "listened_relistened":
                checkins = checkins.filter(
                    Q(status="listened") | Q(status="relistened")
                )
            elif status == "listening_relistening":
                checkins = checkins.filter(
                    Q(status="listening") | Q(status="relistening")
                )
            else:
                checkins = checkins.filter(status=status)

        user_checkin_counts = (
            get_visible_checkins(
                self.request.user, ListenCheckIn, content_type, object_id
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
        object_id = self.kwargs["object_id"]
        model = self.get_model()
        if model is not None:
            context["object"] = model.objects.get(pk=object_id)

        context["order"] = self.request.GET.get("order", "-timestamp")

        context["status"] = self.request.GET.get("status", "")
        context["model_name"] = self.kwargs.get("model_name", "release")

        if context["model_name"] == "release":
            release = model.objects.get(pk=object_id)  # Get the object details
            roles = {}
            for release_role in release.releaserole_set.all():
                if release_role.role.name not in roles:
                    roles[release_role.role.name] = []
                alt_name_or_creator_name = (
                    release_role.alt_name or release_role.creator.name
                )
                roles[release_role.role.name].append(
                    (release_role.creator, alt_name_or_creator_name)
                )
            context["roles"] = roles
        elif context["model_name"] == "audiobook":
            audiobook = model.objects.get(pk=object_id)  # Get the object details
            roles = {}
            for audiobook_role in audiobook.audiobookrole_set.all():
                if audiobook_role.role.name not in roles:
                    roles[audiobook_role.role.name] = []
                alt_name_or_creator_name = (
                    audiobook_role.alt_name or audiobook_role.creator.name
                )
                roles[audiobook_role.role.name].append(
                    (audiobook_role.creator, alt_name_or_creator_name)
                )
            context["roles"] = roles

        include_mathjax, include_mermaid = check_required_js(context["page_obj"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        return context


#################
# Release Group #
#################


class ReleaseGroupCreateView(LoginRequiredMixin, CreateView):
    model = ReleaseGroup
    form_class = ReleaseGroupForm
    template_name = "listen/releasegroup_create.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["releases"] = ReleaseInGroupFormSet(self.request.POST)
        else:
            data["releases"] = ReleaseInGroupFormSet(
                queryset=ReleaseInGroup.objects.none()
            )
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        releases = context["releases"]

        print("Formset data before validation:", releases.data)  # Debugging print

        if releases.is_valid():
            print("Formset cleaned_data:", releases.cleaned_data)  # Debugging print
            with transaction.atomic():
                form.instance.created_by = self.request.user
                self.object = form.save()
                releases.instance = self.object
                releases.save()
        else:
            print("Formset errors:", releases.errors)  # Debugging print
            return self.form_invalid(
                form
            )  # If there are formset errors, re-render the form.
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class ReleaseGroupDetailView(DetailView):
    model = ReleaseGroup
    template_name = "listen/releasegroup_detail.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Get contributors
        context["contributors"] = get_contributors(self.object)

        # Custom sorting logic for releases by date completeness
        # First, fetch all related releases
        releases = self.object.releaseingroup_set.all()

        # Then, sort them by their 'release_date' field length and value
        releases = releases.annotate(
            date_length=Length("release__release_date"),
            padded_date=F("release__release_date"),
        ).order_by("-date_length", "padded_date")

        # Update the context with the sorted releases
        context["sorted_releases"] = releases
        if releases:
            context["oldest_release"] = releases.first()

        return context


class ReleaseGroupUpdateView(LoginRequiredMixin, UpdateView):
    model = ReleaseGroup
    form_class = ReleaseGroupForm
    template_name = "listen/releasegroup_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["releases"] = ReleaseInGroupFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["releases"] = ReleaseInGroupFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        releases = context["releases"]

        print(
            "Formset data before validation for updating:", releases.data
        )  # Debugging print

        if releases.is_valid():
            print(
                "Formset cleaned_data for updating:", releases.cleaned_data
            )  # Debugging print
            self.object = form.save()
            releases.instance = self.object
            releases.save()
        else:
            print("Formset errors:", releases.errors)  # Print out the formset errors.
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("listen:releasegroup_detail", kwargs={"pk": self.object.pk})


#############
# Audiobook #
#############
class AudiobookCreateView(LoginRequiredMixin, CreateView):
    model = Audiobook
    form_class = AudiobookForm
    template_name = "listen/audiobook_create.html"

    def get_success_url(self):
        return reverse_lazy("listen:audiobook_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["audiobookroles"] = AudiobookRoleFormSet(
                self.request.POST, instance=self.object
            )
            data["audiobookinstances"] = AudiobookInstanceFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["audiobookroles"] = AudiobookRoleFormSet(instance=self.object)
            data["audiobookinstances"] = AudiobookInstanceFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        audiobookroles = context["audiobookroles"]
        audiobookinstances = context["audiobookinstances"]

        # Manually check validity of each form in the formset.
        if not all(
            audiobookrole_form.is_valid() for audiobookrole_form in audiobookroles
        ):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if audiobookroles.is_valid():
                audiobookroles.instance = self.object
                audiobookroles.save()
            if audiobookinstances.is_valid():
                audiobookinstances.instance = self.object
                audiobookinstances.save()
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class AudiobookDetailView(DetailView):
    model = Audiobook
    template_name = "listen/audiobook_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["content_type"] = "audiobook"
        audiobook = get_object_or_404(Audiobook, pk=self.kwargs["pk"])

        roles = {}
        for audiobook_role in audiobook.audiobookrole_set.all():
            if audiobook_role.role.name not in roles:
                roles[audiobook_role.role.name] = []
            alt_name_or_creator_name = (
                audiobook_role.alt_name or audiobook_role.creator.name
            )
            roles[audiobook_role.role.name].append(
                (audiobook_role.creator, alt_name_or_creator_name)
            )
        context["roles"] = roles

        content_type = ContentType.objects.get_for_model(Audiobook)
        context["checkin_form"] = ListenCheckInForm(
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": self.request.user.id,
            }
        )

        # Fetch the latest check-in from each user.
        latest_checkin_subquery = (
            get_visible_checkins(
                self.request.user, ListenCheckIn, content_type, self.object.id
            )
            .filter(user=OuterRef("user"))
            .order_by("-timestamp")
        )
        checkins = (
            get_visible_checkins(
                self.request.user, ListenCheckIn, content_type, self.object.id
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
                self.request.user, ListenCheckIn, content_type, self.object.id
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

        # Release check-in status counts, considering only latest check-in per user
        latest_checkin_status_subquery = (
            get_visible_checkins(
                self.request.user,
                ListenCheckIn,
                content_type,
                self.object.id,
                checkin_user=OuterRef("user"),
            )
            .order_by("-timestamp")
            .values("status")[:1]
        )
        latest_checkins = (
            ListenCheckIn.objects.filter(
                content_type=content_type.id, object_id=self.object.id
            )
            .annotate(latest_checkin_status=Subquery(latest_checkin_status_subquery))
            .values("user", "latest_checkin_status")
            .distinct()
        )

        to_listen_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] == "to_listen"
        )
        listening_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["looping", "relistening"]
        )
        listened_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["listened", "relistened"]
        )

        # Add status counts to context
        context.update(
            {
                "to_listen_count": to_listen_count,
                "listening_count": listening_count,
                "listened_count": listened_count,
            }
        )

        # Get the ContentType for the Issue model
        audiobook_content_type = ContentType.objects.get_for_model(Audiobook)

        # Query ContentInList instances that have the audiobook as their content_object
        lists_containing_audiobook = ContentInList.objects.filter(
            content_type=audiobook_content_type, object_id=self.object.id
        ).order_by("luv_list__title")

        context["lists_containing_audiobook"] = lists_containing_audiobook

        # Fetch the latest check-in from the current user for this book
        if self.request.user.is_authenticated:
            latest_user_checkin = (
                ListenCheckIn.objects.filter(
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
                context["latest_user_status"] = "to_listen"
        else:
            context["latest_user_status"] = "to_listen"

        # contributors
        context["contributors"] = get_contributors(self.object)

        context["has_voted"] = user_has_upvoted(self.request.user, self.object)

        context["can_vote"] = (
            self.request.user.is_authenticated
            and ListenCheckIn.objects.filter(
                content_type=ContentType.objects.get_for_model(Audiobook),
                object_id=self.object.id,
                user=self.request.user,
                status__in=["listened", "relistened"],
            ).exists()
        )

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        content_type = ContentType.objects.get_for_model(Audiobook)
        form = ListenCheckInForm(
            data=request.POST,
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": request.user.id,
            },
        )
        if form.is_valid():
            audiobook_check_in = form.save(commit=False)
            audiobook_check_in.user = request.user  # Set the user manually here
            audiobook_check_in.save()

        return redirect(self.object.get_absolute_url())


class AudiobookUpdateView(LoginRequiredMixin, UpdateView):
    model = Audiobook
    form_class = AudiobookForm
    template_name = "listen/audiobook_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("listen:audiobook_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["audiobookroles"] = AudiobookRoleFormSet(
                self.request.POST, instance=self.object
            )
            data["audiobookinstances"] = AudiobookInstanceFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["audiobookroles"] = AudiobookRoleFormSet(instance=self.object)
            data["audiobookinstances"] = AudiobookInstanceFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        audiobookroles = context["audiobookroles"]
        audiobookinstances = context["audiobookinstances"]

        # Manually check validity of each form in the formset.
        if not all(bookrole_form.is_valid() for bookrole_form in audiobookroles):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.updated_by = self.request.user
            if self.request.method == "POST":
                form = AudiobookForm(
                    self.request.POST, self.request.FILES, instance=self.object
                )
                if form.is_valid():
                    self.object = form.save()
                    if audiobookroles.is_valid():
                        audiobookroles.instance = self.object
                        audiobookroles.save()

                    if audiobookinstances.is_valid():
                        audiobookinstances.instance = self.object
                        audiobookinstances.save()

        return super().form_valid(form)


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
class TrackHistoryView(HistoryViewMixin, DetailView):
    model = Track
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class ReleaseHistoryView(HistoryViewMixin, DetailView):
    model = Release
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class ReleaseGroupHistoryView(HistoryViewMixin, DetailView):
    model = ReleaseGroup
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class AudiobookHistoryView(HistoryViewMixin, DetailView):
    model = Audiobook
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context
