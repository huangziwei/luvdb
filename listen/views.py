from collections import defaultdict

from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import F, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from entity.models import Person, Role
from write.forms import CommentForm, RepostForm
from write.models import Comment

from .forms import (
    ListenCheckInForm,
    ReleaseForm,
    ReleaseRoleFormSet,
    ReleaseTrackFormSet,
    TrackForm,
    TrackRoleFormSet,
    WorkForm,
    WorkRoleFormSet,
)
from .models import Label, ListenCheckIn, Release, Track, Work

User = get_user_model()


###########
## Label ##
###########
class LabelCreateView(LoginRequiredMixin, CreateView):
    model = Label
    fields = [
        "name",
        "romanized_name",
        "history",
        "location",
        "website",
        "founded_date",
        "closed_date",
    ]
    template_name = "listen/label_create.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("listen:label_detail", kwargs={"pk": self.object.pk})


class LabelDetailView(DetailView):
    model = Label
    template_name = "listen/label_detail.html"


class LabelAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Label.objects.none()

        qs = Label.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


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


class WorkDetailView(DetailView):
    model = Work
    template_name = "listen/work_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        work = get_object_or_404(Work, pk=self.kwargs.get("pk"))
        # roles
        grouped_roles = defaultdict(list)

        for role in work.workrole_set.all():
            grouped_roles[role.role.name].append(role.person)

        context["grouped_roles"] = dict(grouped_roles)

        # tracks
        tracks = work.tracks.all().order_by("release_date")
        context["tracks"] = []
        for track in tracks:
            releases = track.releases.all()
            for release in releases:
                release.type = "release"
            items = sorted(list(releases), key=lambda x: x.release_date)
            context["tracks"].append({"track": track, "items": items})

        return context


class WorkAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Work.objects.none()

        qs = Work.objects.all()

        if self.q:
            # get all the authors whose name starts with query
            persons = Person.objects.filter(name__istartswith=self.q)

            # get the author role
            singer_role = Role.objects.filter(name="Singer").first()

            # get all the works which are associated with these authors
            qs = qs.filter(
                Q(workrole__role=singer_role, workrole__person__in=persons)
                | Q(title__icontains=self.q)
                | Q(release_date__icontains=self.q)
            ).distinct()

        return qs[:5]

    def get_result_label(self, item):
        # Get the first person with a role of 'Singer' for the release
        singer_role = Role.objects.filter(
            name="Singer"
        ).first()  # Adjust 'Singer' to match your data
        composer_role = Role.objects.filter(name="Composer").first()

        singer_work_role = item.workrole_set.filter(role=singer_role).first()
        composer_work_role = item.workrole_set.filter(role=composer_role).first()
        if singer_work_role:
            person_name = singer_work_role.person.name
        elif composer_work_role:
            person_name = composer_work_role.person.name
        else:
            person_name = "Unknown"

        # Get the year from the release_date
        publication_year = item.release_date[:4] if item.release_date else "Unknown"

        # Format the label
        label = format_html("{} ({}, {})", item.title, person_name, publication_year)

        return label


###########
## Track ##
###########


class TrackCreateView(LoginRequiredMixin, CreateView):
    model = Track
    form_class = TrackForm
    template_name = "listen/track_create.html"

    def get_success_url(self):
        return reverse_lazy("listen:track_detail", kwargs={"pk": self.object.pk})

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


class TrackDetailView(DetailView):
    model = Track
    template_name = "listen/track_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        track = get_object_or_404(Track, pk=self.kwargs.get("pk"))
        # roles
        grouped_roles = defaultdict(list)

        for role in track.trackrole_set.all():
            grouped_roles[role.role.name].append(role.person)

        context["grouped_roles"] = dict(grouped_roles)
        return context


class TrackAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Track.objects.none()

        qs = Track.objects.all()

        if self.q:
            # get all the authors whose name starts with query
            persons = Person.objects.filter(name__istartswith=self.q)

            # get the author role
            singer_role = Role.objects.filter(name="Singer").first()

            # get all the instances which are associated with these authors
            qs = qs.filter(
                Q(trackrole__role=singer_role, trackrole__person__in=persons)
                | Q(title__icontains=self.q)
                | Q(release_date__icontains=self.q)
            ).distinct()

        return qs[:10]

    def get_result_label(self, item):
        # Get the role objects for 'Singer' and 'Composer'
        singer_role = Role.objects.filter(name="Singer").first()
        composer_role = Role.objects.filter(name="Composer").first()

        # Fetch the track_role for 'Singer' and 'Composer'
        singer_track_role = item.trackrole_set.filter(role=singer_role).first()
        composer_track_role = item.trackrole_set.filter(role=composer_role).first()

        # Check if singer_track_role exists and a person is associated
        if singer_track_role:
            person_name = (
                singer_track_role.alt_name
                if singer_track_role.alt_name
                else singer_track_role.person.name
            )
        # If no singer, use composer
        elif composer_track_role:
            person_name = (
                composer_track_role.alt_name
                if composer_track_role.alt_name
                else composer_track_role.person.name
            )
        else:
            person_name = "Unknown"

        # Get the year from the release_date
        release_year = item.release_date[:4] if item.release_date else "Unknown"

        # Format the label
        label = format_html("{} ({}, {})", item.title, person_name, release_year)

        return label


###########
# Release #
###########


class ReleaseCreateView(LoginRequiredMixin, CreateView):
    model = Release
    form_class = ReleaseForm
    template_name = "listen/release_create.html"

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


class ReleaseDetailView(DetailView):
    model = Release
    template_name = "listen/release_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        release = get_object_or_404(Release, pk=self.kwargs["pk"])

        roles = {}
        for release_role in release.releaserole_set.all():
            if release_role.role.name not in roles:
                roles[release_role.role.name] = []
            alt_name_or_person_name = release_role.alt_name or release_role.person.name
            roles[release_role.role.name].append(
                (release_role.person, alt_name_or_person_name)
            )
        context["roles"] = roles

        content_type = ContentType.objects.get_for_model(Release)
        context["checkin_form"] = ListenCheckInForm(
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": self.request.user.id,
            }
        )

        # Fetch the latest check-in from each user.
        latest_checkin_subquery = ListenCheckIn.objects.filter(
            content_type=content_type.id,
            object_id=self.object.id,
            user=OuterRef("user"),
        ).order_by("-timestamp")
        checkins = (
            ListenCheckIn.objects.filter(
                content_type=content_type.id, object_id=self.object.id
            )
            .annotate(
                latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
            )
            .filter(timestamp=F("latest_checkin"))
        ).order_by("-timestamp")[:5]

        context["checkins"] = checkins

        # Release check-in status counts, considering only latest check-in per user
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
                "comments_enabled": True,
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


class ListenCheckInDetailView(DetailView):
    model = ListenCheckIn
    template_name = "listen/listen_checkin_detail.html"
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


class ListenCheckInUpdateView(LoginRequiredMixin, UpdateView):
    model = ListenCheckIn
    form_class = ListenCheckInForm
    template_name = "listen/listen_checkin_update.html"

    def get_success_url(self):
        return reverse_lazy(
            "listen:listen_checkin_detail", kwargs={"pk": self.object.pk}
        )


class ListenCheckInDeleteView(LoginRequiredMixin, DeleteView):
    model = ListenCheckIn
    template_name = "listen/listen_checkin_delete.html"

    def get_success_url(self):
        return reverse_lazy(
            "listen:release_detail", kwargs={"pk": self.object.content_object.pk}
        )


class ListenCheckInListView(ListView):
    model = ListenCheckIn
    template_name = "listen/listen_checkin_list.html"
    context_object_name = "checkins"

    def get_model(self):
        return Release

    def get_queryset(self):
        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        status = self.request.GET.get("status")
        user = get_object_or_404(
            User, username=self.kwargs["username"]
        )  # Get user from url param
        model = self.get_model()
        if model is None:
            checkins = ListenCheckIn.objects.none()
        else:
            content_type = ContentType.objects.get_for_model(model)
            object_id = self.kwargs["release_id"]  # Get object id from url param
            checkins = ListenCheckIn.objects.filter(
                user=user, content_type=content_type, object_id=object_id
            )

        if status:
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
            context["checkins"] = ListenCheckIn.objects.none()
            context["object"] = None
        else:
            content_type = ContentType.objects.get_for_model(model)
            object_id = self.kwargs["release_id"]  # Get object id from url param
            context[
                "checkins"
            ] = self.get_queryset()  # Use the queryset method to handle status filter
            release = model.objects.get(pk=object_id)  # Get the object details
            context["object"] = release

            roles = {}
            for release_role in release.releaserole_set.all():
                if release_role.role.name not in roles:
                    roles[release_role.role.name] = []
                alt_name_or_person_name = (
                    release_role.alt_name or release_role.person.name
                )
                roles[release_role.role.name].append(
                    (release_role.person, alt_name_or_person_name)
                )
            context["roles"] = roles

        context["model_name"] = self.kwargs.get("model_name", "release")

        return context


class ListenCheckInAllListView(ListView):
    model = ListenCheckIn
    template_name = "listen/listen_checkin_list_all.html"
    context_object_name = "checkins"

    def get_model(self):
        return Release

    def get_queryset(self):
        model = self.get_model()
        if model is None:
            return ListenCheckIn.objects.none()

        content_type = ContentType.objects.get_for_model(model)
        object_id = self.kwargs["release_id"]  # Get object id from url param

        latest_checkin_subquery = ListenCheckIn.objects.filter(
            content_type=content_type, object_id=object_id, user=OuterRef("user")
        ).order_by("-timestamp")

        checkins = (
            ListenCheckIn.objects.filter(content_type=content_type, object_id=object_id)
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
            checkins = checkins.filter(status=status)

        return checkins

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object_id = self.kwargs["release_id"]

        model = self.get_model()
        if model is not None:
            release = model.objects.get(pk=object_id)  # Get the object details
            context["object"] = release

            roles = {}
            for release_role in release.releaserole_set.all():
                if release_role.role.name not in roles:
                    roles[release_role.role.name] = []
                alt_name_or_person_name = (
                    release_role.alt_name or release_role.person.name
                )
                roles[release_role.role.name].append(
                    (release_role.person, alt_name_or_person_name)
                )
            context["roles"] = roles

        context["order"] = self.request.GET.get(
            "order", "-timestamp"
        )  # Default is '-timestamp'

        context["status"] = self.request.GET.get("status", "")
        context["model_name"] = self.kwargs.get("model_name", "release")

        return context


class ListenListView(ListView):
    template_name = "listen/listen_list.html"
    context_object_name = "objects"

    def get_queryset(self):
        recent_releases = Release.objects.all().order_by("-created_at")[:12]

        return {"recent_releases": recent_releases}


class ListenCheckInUserListView(ListView):
    """
    All latest check-ins from a given user of all books and issues.
    """

    model = ListenCheckIn
    template_name = "listen/listen_checkin_list_user.html"
    context_object_name = "checkins"

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs["username"])

        latest_checkin_subquery = ListenCheckIn.objects.filter(
            user=user,
            content_type=OuterRef("content_type"),
            object_id=OuterRef("object_id"),
        ).order_by("-timestamp")

        checkins = (
            ListenCheckIn.objects.filter(user=user)
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
