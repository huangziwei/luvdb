from datetime import timedelta
from typing import Any

from dal import autocomplete
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count, F, Max, Min, OuterRef, Q, Subquery
from django.db.models.functions import Length
from django.forms import inlineformset_factory
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
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
)
from django_ratelimit.decorators import ratelimit

from activity_feed.models import Block
from discover.utils import user_has_upvoted
from entity.models import LanguageField
from entity.utils import get_company_name
from entity.views import HistoryViewMixin, get_contributors
from listen.models import Release, Track
from listen.models import Work as MusicWork
from play.models import Work as GameWork
from visit.models import Location
from visit.utils import get_locations_with_parents
from watch.models import Movie, Series
from write.forms import CommentForm, RepostForm
from write.models import Comment, ContentInList
from write.utils import get_visible_checkins, get_visible_comments
from write.utils_bluesky import create_bluesky_post
from write.utils_formatting import check_required_js
from write.utils_mastodon import create_mastodon_post

from .forms import (
    BookForm,
    BookGroupForm,
    BookInGroupForm,
    BookInGroupFormSet,
    BookInSeriesFormSet,
    BookInstance,
    BookInstanceFormSet,
    BookRole,
    BookRoleForm,
    BookRoleFormSet,
    BookSeriesForm,
    InstanceForm,
    InstanceRole,
    InstanceRoleForm,
    InstanceRoleFormSet,
    IssueForm,
    IssueInstance,
    IssueInstanceFormSet,
    PeriodicalForm,
    ReadCheckInForm,
    WorkForm,
    WorkRoleFormSet,
)
from .models import (
    Book,
    BookGroup,
    BookInGroup,
    BookInSeries,
    BookSeries,
    Creator,
    Genre,
    Instance,
    Issue,
    Periodical,
    ReadCheckIn,
    Role,
    Work,
)

User = get_user_model()

##########
## Work ##
##########


class WorkCreateView(LoginRequiredMixin, CreateView):
    model = Work
    form_class = WorkForm
    template_name = "read/work_create.html"

    def get_success_url(self):
        return reverse_lazy("read:work_detail", kwargs={"pk": self.object.pk})

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
    template_name = "read/work_update.html"

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
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("read:work_detail", kwargs={"pk": self.object.pk})


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class WorkDetailView(DetailView):
    model = Work
    template_name = "read/work_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        work = get_object_or_404(Work, pk=self.kwargs.get("pk"))
        instances = work.instances.all().order_by("publication_date")
        language_grouped_instances = {}

        for instance in instances:
            lang = instance.language
            if lang not in language_grouped_instances:
                language_grouped_instances[lang] = []

            books = instance.books.all().order_by("publication_date")
            for book in books:
                book.type = "book"

            issues = instance.issues.all().order_by("publication_date")
            for issue in issues:
                issue.type = "issue"

            audiobooks = instance.audiobooks.all().order_by("release_date")
            for audiobook in audiobooks:  # newly added
                audiobook.type = "audiobook"

            sorted_instance_roles = instance.instancerole_set.all().order_by(
                "role__name"
            )

            def sorting_key(item):
                if item.type == "audiobook":
                    return item.release_date
                return item.publication_date

            items = sorted(
                list(books) + list(issues) + list(audiobooks), key=sorting_key
            )
            language_grouped_instances[lang].append(
                {
                    "instance": instance,
                    "items": items,
                    "instance_roles": sorted_instance_roles,
                }
            )

        context["grouped_instances"] = language_grouped_instances

        # adaptations
        adaptation_movies = (
            Movie.objects.filter(based_on_litworks=self.object)
            .annotate(release_date=Min("region_release_dates__release_date"))
            .order_by("release_date")
        )
        adaptation_series = Series.objects.filter(
            based_on_litworks=self.object
        ).order_by("release_date")
        adaptation_games = GameWork.objects.filter(
            based_on_litworks=self.object
        ).order_by("first_release_date")
        adaptation_publications = Work.objects.filter(
            based_on_litworks=self.object
        ).order_by("publication_date")
        context["adaptation_movies"] = adaptation_movies
        context["adaptation_series"] = adaptation_series
        context["adaptation_games"] = adaptation_games
        context["adaptation_publications"] = adaptation_publications

        # mentions
        context["mentioned_litworks"] = work.mentioned_litworks.order_by(
            "publication_date"
        )
        context["mentioned_instances"] = work.mentioned_litinstances.order_by(
            "publication_date"
        )
        context["mentioned_movies"] = work.mentioned_movies.annotate(
            annotated_earliest_release_date=Min("region_release_dates__release_date")
        ).order_by("annotated_earliest_release_date")
        context["mentioned_series"] = work.mentioned_series.order_by("release_date")
        context["mentioned_musicworks"] = work.mentioned_musicalworks.order_by(
            "release_date"
        )
        context["mentioned_tracks"] = work.mentioned_tracks.order_by("release_date")
        context["mentioned_releases"] = work.mentioned_releases.order_by("release_date")

        grouped_roles = {}
        for role in work.workrole_set.all():
            if role.role.name not in grouped_roles:
                grouped_roles[role.role.name] = []
            alt_name_or_creator_name = role.alt_name or role.creator.name
            grouped_roles[role.role.name].append(
                (role.creator, alt_name_or_creator_name)
            )
        context["grouped_roles"] = grouped_roles

        # contributors
        context["contributors"] = get_contributors(self.object)

        context["related_locations_with_parents"] = get_locations_with_parents(
            self.object.related_locations
        )
        return context


#############
## Instance ##
#############


class InstanceCreateView(LoginRequiredMixin, CreateView):
    model = Instance
    form_class = InstanceForm
    template_name = "read/instance_create.html"

    def get_success_url(self):
        return reverse_lazy("read:instance_detail", kwargs={"pk": self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        work_id = self.kwargs.get(
            "work_id"
        )  # Assuming 'work_id' is passed as URL parameter

        if not work_id and "work_id" in self.request.session:
            # If 'work_id' is not in URL parameters, try getting it from the session
            work_id = self.request.session["work_id"]

        if work_id:
            work = get_object_or_404(Work, id=work_id)
            initial.update(
                {
                    "work": work,
                    "title": work.title,
                    "subtitle": work.subtitle,
                    "publication_date": work.publication_date,
                    "language": work.language,
                    "wikipedia": work.wikipedia,
                }
            )

        return initial

    def get_context_data(self, **kwargs):
        data = super(InstanceCreateView, self).get_context_data(**kwargs)
        if self.request.POST:
            data["instanceroles"] = InstanceRoleFormSet(
                self.request.POST, self.request.FILES, instance=self.object
            )
        else:
            work_id = self.kwargs.get("work_id")
            if work_id:
                work = get_object_or_404(Work, id=work_id)
                work_roles = work.workrole_set.all()

                initial_roles = [
                    {
                        "creator": work_role.creator,
                        "role": work_role.role,
                        "alt_name": work_role.alt_name,
                    }
                    for work_role in work_roles
                ]
                InstanceRoleFormSet_prefilled = inlineformset_factory(
                    Instance,
                    InstanceRole,
                    form=InstanceRoleForm,
                    extra=len(initial_roles),
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

                data["instanceroles"] = InstanceRoleFormSet_prefilled(
                    instance=self.object,
                    queryset=InstanceRole.objects.none(),
                    initial=initial_roles,
                )
            else:
                data["instanceroles"] = InstanceRoleFormSet(
                    instance=self.object,
                    queryset=InstanceRole.objects.none(),
                )
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        instanceroles = context["instanceroles"]

        # Manually check validity of each form in the formset.
        if not all(instancerole_form.is_valid() for instancerole_form in instanceroles):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if instanceroles.is_valid():
                instanceroles.instance = self.object
                instanceroles.save()
        return super().form_valid(form)


class InstanceUpdateView(LoginRequiredMixin, UpdateView):
    model = Instance
    form_class = InstanceForm
    template_name = "read/instance_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the Work object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["instanceroles"] = InstanceRoleFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["instanceroles"] = InstanceRoleFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        instanceroles = context["instanceroles"]

        # Manually check validity of each form in the formset.
        if not all(instancerole_form.is_valid() for instancerole_form in instanceroles):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if instanceroles.is_valid():
                instanceroles.instance = self.object
                instanceroles.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("read:instance_detail", kwargs={"pk": self.object.pk})


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class InstanceDetailView(DetailView):
    model = Instance
    template_name = "read/instance_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = get_object_or_404(Instance, pk=self.kwargs.get("pk"))
        grouped_roles = {}
        for role in instance.instancerole_set.all():
            if role.role.name not in grouped_roles:
                grouped_roles[role.role.name] = []
            alt_name_or_creator_name = role.alt_name or role.creator.name
            grouped_roles[role.role.name].append(
                (role.creator, alt_name_or_creator_name)
            )
        context["grouped_roles"] = grouped_roles
        context["books"] = instance.books.all().order_by("publication_date")
        context["issues"] = instance.issues.all().order_by("publication_date")
        context["audiobooks"] = instance.audiobooks.all().order_by("release_date")

        # contributors
        context["contributors"] = get_contributors(self.object)

        instance_checkins = []
        # Filter ReadCheckIns for BookInstance
        book_instances = BookInstance.objects.filter(instance=instance)
        for book_instance in book_instances:
            check_ins_for_book = ReadCheckIn.objects.filter(
                content_type=ContentType.objects.get_for_model(Book),
                object_id=book_instance.book.id,
                progress_type="CH",
                progress=str(book_instance.order),
            )
            instance_checkins.extend(check_ins_for_book)

        # Filter ReadCheckIns for IssueInstance
        issue_instances = IssueInstance.objects.filter(instance=instance)
        for issue_instance in issue_instances:
            check_ins_for_issue = ReadCheckIn.objects.filter(
                content_type=ContentType.objects.get_for_model(Issue),
                object_id=issue_instance.issue.id,
                progress_type="CH",
                progress=str(issue_instance.order),
            )
            instance_checkins.extend(check_ins_for_issue)

        instance_checkins.sort(key=lambda x: x.timestamp, reverse=True)
        context["instance_checkins"] = instance_checkins

        if instance.work:
            context["related_locations_with_parents"] = get_locations_with_parents(
                instance.work.related_locations
            )
        return context


########
# Book #
########


class BookCreateView(LoginRequiredMixin, CreateView):
    model = Book
    form_class = BookForm
    template_name = "read/book_create.html"

    def get_success_url(self):
        return reverse_lazy("read:book_detail", kwargs={"pk": self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        instance_id = self.kwargs.get("instance_id")

        if instance_id:
            source_instance = get_object_or_404(Instance, id=instance_id)
            initial.update(
                {
                    "title": source_instance.title,
                    "subtitle": source_instance.subtitle,
                    "publication_date": source_instance.publication_date,
                    "language": source_instance.language,
                    "wikipedia": source_instance.wikipedia,
                }
            )

        return initial

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        instance_id = self.kwargs.get("instance_id")

        if self.request.POST:
            data["bookroles"] = BookRoleFormSet(self.request.POST, instance=self.object)
            data["bookinstances"] = BookInstanceFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["bookroles"] = BookRoleFormSet(instance=self.object)
            data["bookinstances"] = BookInstanceFormSet(instance=self.object)

            if instance_id:
                source_instance = get_object_or_404(Instance, id=instance_id)
                # Prefill bookroles from InstanceRoles
                instance_roles = source_instance.instancerole_set.all()
                initial_roles = [
                    {
                        "creator": role.creator.id,
                        "role": role.role.id,
                        "alt_name": role.alt_name,
                    }
                    for role in instance_roles
                ]

                BookRoleFormSet_prefilled = inlineformset_factory(
                    Book,
                    BookRole,
                    form=BookRoleForm,
                    extra=len(initial_roles),
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

                data["bookroles"] = BookRoleFormSet_prefilled(
                    instance=self.object, initial=initial_roles
                )

                # Prefill bookinstances with the source instance
                initial_instances = [{"instance": source_instance}]
                data["bookinstances"] = BookInstanceFormSet(
                    instance=self.object,
                    initial=initial_instances,
                    queryset=BookInstance.objects.none(),
                )

        return data

    def form_valid(self, form):
        context = self.get_context_data()
        bookroles = context["bookroles"]
        bookinstances = context["bookinstances"]

        # Manually check validity of each form in the formset.
        if not all(bookrole_form.is_valid() for bookrole_form in bookroles):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()

            if bookroles.is_valid():
                bookroles.instance = self.object
                bookroles.save()

            if bookinstances.is_valid():
                bookinstances.instance = self.object
                bookinstances.save()

        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class BookDetailView(DetailView):
    model = Book
    template_name = "read/book_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        book = get_object_or_404(Book, pk=self.kwargs["pk"])

        main_role_names = [
            "Author",
            "Translator",
            "Illustrator",
            "Editor",
            "Story By",
            "Novelization By",
            "Ghost Writer",
            "Annotator",
        ]
        main_roles = {}
        other_roles = {}

        for book_role in book.bookrole_set.all():
            role_name = book_role.role.name
            alt_name_or_creator_name = book_role.alt_name or book_role.creator.name

            if role_name in main_role_names:
                if role_name not in main_roles:
                    main_roles[role_name] = []
                main_roles[role_name].append(
                    (book_role.creator, alt_name_or_creator_name)
                )
            else:
                if role_name not in other_roles:
                    other_roles[role_name] = []
                other_roles[role_name].append(
                    (book_role.creator, alt_name_or_creator_name)
                )

        context["main_roles"] = main_roles
        context["other_roles"] = other_roles

        content_type = ContentType.objects.get_for_model(Book)
        context["checkin_form"] = ReadCheckInForm(
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
                self.request.user, ReadCheckIn, content_type, self.object.id
            )
            .filter(user=OuterRef("user"))
            .order_by("-timestamp")
        )

        checkins = (
            get_visible_checkins(
                self.request.user, ReadCheckIn, content_type, self.object.id
            )
            .annotate(
                latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
            )
            .filter(timestamp=F("latest_checkin"))
            .order_by("-timestamp")
        )
        context["checkins"] = context["page_obj"] = checkins

        user_checkin_counts = (
            get_visible_checkins(
                self.request.user, ReadCheckIn, content_type, self.object.id
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

        # Book check-in status counts, considering only latest check-in per user
        latest_checkin_status_subquery = (
            get_visible_checkins(
                self.request.user,
                ReadCheckIn,
                content_type,
                self.object.id,
                checkin_user=OuterRef("user"),
            )
            .order_by("-timestamp")
            .values("status")[:1]
        )
        latest_checkins = (
            ReadCheckIn.objects.filter(
                content_type=content_type.id, object_id=self.object.id
            )
            .annotate(latest_checkin_status=Subquery(latest_checkin_status_subquery))
            .values("user", "latest_checkin_status")
            .distinct()
        )

        to_read_count = sum(
            1 for item in latest_checkins if item["latest_checkin_status"] == "to_read"
        )
        reading_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["reading", "rereading"]
        )
        read_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["finished_reading", "reread"]
        )

        # Add status counts to context
        context.update(
            {
                "to_read_count": to_read_count,
                "reading_count": reading_count,
                "read_count": read_count,
                "checkins": checkins,
            }
        )

        # Query ContentInList instances that have the book as their content_object
        lists_containing_book = ContentInList.objects.filter(
            content_type=content_type, object_id=book.id
        )

        context["lists_containing_book"] = lists_containing_book

        # Fetch the latest check-in from the current user for this book
        if self.request.user.is_authenticated:
            latest_user_checkin = (
                ReadCheckIn.objects.filter(
                    content_type=content_type.id,
                    object_id=self.object.id,
                    user=self.request.user,
                )
                .order_by("-timestamp")
                .first()
            )
            if latest_user_checkin is not None:
                context["latest_user_status"] = latest_user_checkin.status
                context["latest_progress_type"] = latest_user_checkin.progress_type
            else:
                context["latest_user_status"] = "to_read"
                context["latest_progress_type"] = "PG"
        else:
            context["latest_user_status"] = "to_read"
            context["latest_progress_type"] = "PG"

        # contributors
        context["contributors"] = get_contributors(self.object)

        include_mathjax, include_mermaid = check_required_js(context["checkins"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        genres = set()
        for instance in book.instances.all():
            if instance.work:  # Check if the instance has an associated work
                for genre in instance.work.genres.all():
                    genres.add(genre)
        context["genres"] = genres

        unique_locations_with_parents_set = set()
        unique_related_publications_set = set()
        unique_related_games_set = set()
        unique_related_movies_set = set()
        unique_related_series_set = set()
        unique_based_on_publications_set = set()
        unique_based_on_games_set = set()
        unique_based_on_movies_set = set()
        unique_based_on_series_set = set()
        unique_mentioned_publications_set = set()
        unique_mentioned_instances_set = set()
        unique_mentioned_movies_set = set()
        unique_mentioned_series_set = set()
        unique_mentioned_musicworks_set = set()
        unique_mentioned_tracks_set = set()
        unique_mentioned_releases_set = set()
        for instance in book.instances.all():
            # visit
            locations_with_parents = get_locations_with_parents(
                instance.work.related_locations
            )
            # read
            unique_related_publications_set.update(
                instance.work.related_publications.values_list("pk", flat=True)
            )
            unique_based_on_publications_set.update(
                instance.work.based_on_litworks.values_list("pk", flat=True)
            )
            unique_mentioned_publications_set.update(
                instance.work.mentioned_litworks.values_list("pk", flat=True)
            )
            unique_mentioned_instances_set.update(
                instance.work.mentioned_litinstances.values_list("pk", flat=True)
            )
            # play
            unique_related_games_set.update(
                instance.work.games.values_list("pk", flat=True)
            )
            unique_based_on_games_set.update(
                instance.work.based_on_games.values_list("pk", flat=True)
            )
            # watch
            unique_related_movies_set.update(
                instance.work.movies.values_list("pk", flat=True)
            )
            unique_based_on_movies_set.update(
                instance.work.based_on_movies.values_list("pk", flat=True)
            )
            unique_mentioned_movies_set.update(
                instance.work.mentioned_movies.values_list("pk", flat=True)
            )
            unique_related_series_set.update(
                instance.work.series.values_list("pk", flat=True)
            )
            unique_based_on_series_set.update(
                instance.work.based_on_series.values_list("pk", flat=True)
            )
            unique_mentioned_series_set.update(
                instance.work.mentioned_series.values_list("pk", flat=True)
            )
            # listen
            unique_mentioned_musicworks_set.update(
                instance.work.mentioned_musicalworks.values_list("pk", flat=True)
            )
            unique_mentioned_tracks_set.update(
                instance.work.mentioned_tracks.values_list("pk", flat=True)
            )
            unique_mentioned_releases_set.update(
                instance.work.mentioned_releases.values_list("pk", flat=True)
            )

            # Process each location with its parents
            for location, parents in locations_with_parents:
                # Convert location and its parents to their unique identifiers
                location_id = location.pk  # Assuming pk is the primary key
                parent_ids = tuple(parent.pk for parent in parents)

                # Add the tuple of identifiers to the set
                unique_locations_with_parents_set.add((location_id, parent_ids))

        # Convert back to the original Location objects
        context["related_locations_with_parents"] = [
            (
                Location.objects.get(pk=location_id),
                [Location.objects.get(pk=parent_id) for parent_id in parent_ids],
            )
            for location_id, parent_ids in unique_locations_with_parents_set
        ]
        context["related_publications"] = sorted(
            [Work.objects.get(pk=pk) for pk in unique_related_publications_set],
            key=lambda work: work.publication_date,
        )
        context["related_games"] = sorted(
            [GameWork.objects.get(pk=pk) for pk in unique_related_games_set],
            key=lambda work: work.first_release_date,
        )
        context["related_movies"] = sorted(
            [Movie.objects.get(pk=pk) for pk in unique_related_movies_set],
            key=lambda movie: movie.region_release_dates.order_by("release_date")
            .first()
            .release_date,
        )
        context["related_series"] = sorted(
            [Series.objects.get(pk=pk) for pk in unique_related_series_set],
            key=lambda series: series.release_date,
        )
        context["based_on_publications"] = sorted(
            [Work.objects.get(pk=pk) for pk in unique_based_on_publications_set],
            key=lambda work: work.publication_date,
        )

        context["based_on_games"] = sorted(
            [GameWork.objects.get(pk=pk) for pk in unique_based_on_games_set],
            key=lambda work: work.first_release_date,
        )
        context["based_on_movies"] = sorted(
            [Movie.objects.get(pk=pk) for pk in unique_based_on_movies_set],
            key=lambda movie: movie.region_release_dates.order_by("release_date")
            .first()
            .release_date,
        )
        context["based_on_series"] = sorted(
            [Series.objects.get(pk=pk) for pk in unique_based_on_series_set],
            key=lambda series: series.release_date,
        )
        context["mentioned_litworks"] = sorted(
            [Work.objects.get(pk=pk) for pk in unique_mentioned_publications_set],
            key=lambda work: work.publication_date,
        )
        context["mentioned_litinstances"] = sorted(
            [Instance.objects.get(pk=pk) for pk in unique_mentioned_instances_set],
            key=lambda instance: instance.publication_date,
        )
        context["mentioned_series"] = sorted(
            [Series.objects.get(pk=pk) for pk in unique_mentioned_series_set],
            key=lambda series: series.release_date,
        )
        context["mentioned_movies"] = sorted(
            [Movie.objects.get(pk=pk) for pk in unique_mentioned_movies_set],
            key=lambda movie: movie.region_release_dates.order_by("release_date")
            .first()
            .release_date,
        )
        context["mentioned_musicworks"] = sorted(
            [MusicWork.objects.get(pk=pk) for pk in unique_mentioned_musicworks_set],
            key=lambda work: work.release_date,
        )
        context["mentioned_tracks"] = sorted(
            [Track.objects.get(pk=pk) for pk in unique_mentioned_tracks_set],
            key=lambda track: track.release_date,
        )
        context["mentioned_releases"] = sorted(
            [Release.objects.get(pk=pk) for pk in unique_mentioned_releases_set],
            key=lambda release: release.release_date,
        )

        context["has_voted"] = user_has_upvoted(self.request.user, self.object)
        # can vote only if user checked in "read" or "reread"
        context["can_vote"] = (
            self.request.user.is_authenticated
            and ReadCheckIn.objects.filter(
                content_type=ContentType.objects.get_for_model(Book),
                object_id=self.object.id,
                user=self.request.user,
                status__in=["finished_reading", "reread"],
            ).exists()
        )
        context["publisher"] = get_company_name(
            [book.publisher], book.publication_date
        )[0]

        # mentions by other media
        context["mentioned_by_movies"] = (
            self.object.mentioned_in_movies.distinct()
            .annotate(annotated_release_date=Min("region_release_dates__release_date"))
            .order_by("annotated_release_date")
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        content_type = ContentType.objects.get_for_model(Book)
        form = ReadCheckInForm(
            data=request.POST,
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": request.user.id,
                "comments_enabled": True,
            },
        )
        if form.is_valid():
            book_check_in = form.save(commit=False)
            book_check_in.user = request.user  # Set the user manually here
            book_check_in.save()

        return redirect(self.object.get_absolute_url())


class BookUpdateView(LoginRequiredMixin, UpdateView):
    model = Book
    form_class = BookForm
    template_name = "read/book_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the Work object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("read:book_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["bookroles"] = BookRoleFormSet(self.request.POST, instance=self.object)
            data["bookinstances"] = BookInstanceFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["bookroles"] = BookRoleFormSet(instance=self.object)
            data["bookinstances"] = BookInstanceFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        bookroles = context["bookroles"]
        bookinstances = context["bookinstances"]

        # Manually check validity of each form in the formset.
        if not all(bookrole_form.is_valid() for bookrole_form in bookroles):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.updated_by = self.request.user

            if bookroles.is_valid():
                bookroles.instance = self.object
                bookroles.save()

            if bookinstances.is_valid():
                bookinstances.instance = self.object
                bookinstances.save()

        return super().form_valid(form)


class PeriodicalCreateView(LoginRequiredMixin, CreateView):
    model = Periodical
    # fields = "__all__"
    form_class = PeriodicalForm
    template_name = "read/periodical_create.html"

    def get_success_url(self):
        return reverse_lazy("read:periodical_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class PeriodicalDetailView(DetailView):
    model = Periodical
    template_name = "read/periodical_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["issues"] = self.object.issues.all().order_by("publication_date")
        # contributors
        context["contributors"] = get_contributors(self.object)
        return context


class PeriodicalUpdateView(LoginRequiredMixin, UpdateView):
    model = Periodical
    form_class = PeriodicalForm
    template_name = "read/periodical_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("read:periodical_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class IssueCreateView(LoginRequiredMixin, CreateView):
    model = Issue
    form_class = IssueForm
    template_name = "read/periodical_issue_create.html"

    def get_initial(self):
        initial = super().get_initial()
        periodical_id = self.kwargs.get("periodical_id")
        initial["periodical"] = get_object_or_404(Periodical, pk=periodical_id)
        return initial

    def get_form(self, form_class=None):
        form = super(IssueCreateView, self).get_form(form_class)
        form.fields["periodical"].disabled = True
        return form

    def get_success_url(self):
        periodical_id = self.kwargs.get("periodical_id")
        return reverse(
            "read:issue_detail",
            kwargs={
                "pk": self.object.pk,
                "periodical_id": periodical_id,
            },
        )

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["issueinstances"] = IssueInstanceFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["issueinstances"] = IssueInstanceFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        context = self.get_context_data()
        issueinstances = context["issueinstances"]
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if issueinstances.is_valid():
                issueinstances.instance = self.object
                issueinstances.save()

        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class IssueDetailView(DetailView):
    model = Issue
    template_name = "read/periodical_issue_detail.html"
    context_object_name = "issue"

    def get_queryset(self):
        self.periodical = get_object_or_404(Periodical, pk=self.kwargs["periodical_id"])
        return self.periodical.issues.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["periodical"] = self.periodical

        content_type = ContentType.objects.get_for_model(Issue)
        context["checkin_form"] = ReadCheckInForm(
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": self.request.user.id,
            }
        )

        # Fetch the latest check-in from each user.
        latest_checkin_subquery = (
            get_visible_checkins(
                self.request.user, ReadCheckIn, content_type, self.object.id
            )
            .filter(user=OuterRef("user"))
            .order_by("-timestamp")
        )
        checkins = (
            get_visible_checkins(
                self.request.user, ReadCheckIn, content_type, self.object.id
            )
            .annotate(
                latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
            )
            .filter(timestamp=F("latest_checkin"))
        ).order_by("-timestamp")[:5]

        # Get the count of check-ins for each user for this issue
        user_checkin_counts = (
            get_visible_checkins(
                self.request.user, ReadCheckIn, content_type, self.object.id
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

        # Issue check-in status counts, considering only latest check-in per user
        latest_checkin_status_subquery = (
            get_visible_checkins(
                self.request.user,
                ReadCheckIn,
                content_type,
                self.object.id,
                checkin_user=OuterRef("user"),
            )
            .order_by("-timestamp")
            .values("status")[:1]
        )
        latest_checkins = (
            ReadCheckIn.objects.filter(
                content_type=content_type.id, object_id=self.object.id
            )
            .annotate(latest_checkin_status=Subquery(latest_checkin_status_subquery))
            .values("user", "latest_checkin_status")
            .distinct()
        )

        to_read_count = sum(
            1 for item in latest_checkins if item["latest_checkin_status"] == "to_read"
        )
        reading_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["reading", "rereading"]
        )
        read_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["finished_reading", "reread"]
        )

        # Add status counts to context
        context.update(
            {
                "to_read_count": to_read_count,
                "reading_count": reading_count,
                "read_count": read_count,
                "checkins": checkins,
            }
        )

        # Get the ContentType for the Issue model
        issue_content_type = ContentType.objects.get_for_model(Issue)

        # Query ContentInList instances that have the issue as their content_object
        lists_containing_issue = ContentInList.objects.filter(
            content_type=issue_content_type, object_id=self.object.id
        ).order_by("luv_list__title")

        context["lists_containing_issue"] = lists_containing_issue

        # Fetch the latest check-in from the current user for this book
        if self.request.user.is_authenticated:
            latest_user_checkin = (
                ReadCheckIn.objects.filter(
                    content_type=content_type.id,
                    object_id=self.object.id,
                    user=self.request.user,
                )
                .order_by("-timestamp")
                .first()
            )
            if latest_user_checkin is not None:
                context["latest_user_status"] = latest_user_checkin.status
                context["latest_progress_type"] = latest_user_checkin.progress_type
            else:
                context["latest_user_status"] = "to_read"
                context["latest_progress_type"] = "PG"
        else:
            context["latest_user_status"] = "to_read"
            context["latest_progress_type"] = "PG"

        # contributors
        context["contributors"] = get_contributors(self.object)

        context["has_voted"] = user_has_upvoted(self.request.user, self.object)
        context["can_vote"] = (
            self.request.user.is_authenticated
            and ReadCheckIn.objects.filter(
                content_type=ContentType.objects.get_for_model(Issue),
                object_id=self.object.id,
                user=self.request.user,
                status__in=["finished_reading", "reread"],
            ).exists()
        )

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        content_type = ContentType.objects.get_for_model(Issue)
        form = ReadCheckInForm(
            data=request.POST,
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": request.user.id,
                "comments_enabled": True,
            },
        )
        if form.is_valid():
            book_check_in = form.save(commit=False)
            book_check_in.user = request.user  # Set the user manually here
            book_check_in.save()

        return redirect(self.object.get_absolute_url())


class IssueUpdateView(LoginRequiredMixin, UpdateView):
    model = Issue
    form_class = IssueForm
    template_name = "read/periodical_issue_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the Work object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["periodical"].disabled = True
        return form

    def get_success_url(self):
        periodical_id = self.object.periodical.pk
        return reverse(
            "read:issue_detail",
            kwargs={
                "pk": self.object.pk,
                "periodical_id": periodical_id,
            },
        )

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["issueinstances"] = IssueInstanceFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["issueinstances"] = IssueInstanceFormSet(instance=self.object)

        return data

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        context = self.get_context_data()
        issueinstances = context["issueinstances"]
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if issueinstances.is_valid():
                issueinstances.instance = self.object
                issueinstances.save()

        return super().form_valid(form)


################
# AutoComplete #
################


class WorkAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Work.objects.none()

        qs = Work.objects.all()

        if self.q:
            # get all the authors whose name starts with query
            authors = Creator.objects.filter(name__icontains=self.q)

            # get the author role
            author_role = Role.objects.filter(name="Author").first()

            # get all the works which are associated with these authors
            qs = qs.filter(
                Q(workrole__role=author_role, workrole__creator__in=authors)
                | Q(title__icontains=self.q)
                | Q(publication_date__icontains=self.q)
            ).distinct()

            return qs

        return Work.objects.none()

    def get_result_label(self, item):
        # Get the first person with a role of 'Author' for the book
        author_role = Role.objects.filter(
            name="Author"
        ).first()  # Adjust 'Author' to match your data
        work_role = item.workrole_set.filter(role=author_role).first()

        author_name = None
        if work_role:
            author_name = work_role.alt_name or work_role.creator.name

        # Get the year from the publication_date
        publication_year = (
            item.publication_date.split(".")[0] if item.publication_date else "?"
        )

        # Format the label
        if author_name:
            label = "{} ({} - {})".format(item.title, author_name, publication_year)
        else:
            label = "{} ({})".format(item.title, publication_year)

        return mark_safe(label)


class InstanceAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Instance.objects.none()

        qs = Instance.objects.all()

        if self.q:
            # get all the authors whose name starts with query
            authors = Creator.objects.filter(name__icontains=self.q)

            # get the author role
            author_role = Role.objects.filter(name="Author").first()

            # get all the instances which are associated with these authors
            qs = qs.filter(
                Q(instancerole__role=author_role, instancerole__creator__in=authors)
                | Q(title__icontains=self.q)
                | Q(publication_date__icontains=self.q)
            ).distinct()

            return qs

        return Instance.objects.none()

    def get_result_label(self, item):
        # Get the first person with a role of 'Author' for the book
        author_role = Role.objects.filter(
            name="Author"
        ).first()  # Adjust 'Author' to match your data

        instance_role = item.instancerole_set.filter(role=author_role).first()

        author_name = None
        if instance_role:
            author_name = instance_role.alt_name or instance_role.creator.name

        # Get the year from the publication_date
        publication_year = (
            item.publication_date.split(".")[0] if item.publication_date else "?"
        )

        # Format the label
        if author_name:
            label = "{} ({} - {})".format(item.title, author_name, publication_year)
        else:
            label = "{} ({})".format(item.title, publication_year)

        return mark_safe(label)


class BookAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Book.objects.none()

        qs = Book.objects.all()

        if self.q:
            # get all the authors whose name starts with query
            authors = Creator.objects.filter(name__icontains=self.q)

            # get the author role
            author_role = Role.objects.filter(name="Author").first()

            # get all the instances which are associated with these authors
            qs = qs.filter(
                Q(bookrole__role=author_role, bookrole__creator__in=authors)
                | Q(title__icontains=self.q)
                | Q(publication_date__icontains=self.q)
            ).distinct()

            return qs

        return Instance.objects.none()

    def get_result_label(self, item):
        # Get the first person with a role of 'Author' for the book
        author_role = Role.objects.filter(
            name="Author"
        ).first()  # Adjust 'Author' to match your data

        book_role = item.bookrole_set.filter(role=author_role).first()

        author_name = None
        if book_role:
            author_name = book_role.alt_name or book_role.creator.name

        # Get the year from the publication_date
        publication_year = (
            item.publication_date.split(".")[0] if item.publication_date else "?"
        )

        # Format the label
        if author_name:
            label = "{} ({} - {})".format(item.title, author_name, publication_year)
        else:
            label = "{} ({})".format(item.title, publication_year)

        return mark_safe(label)


class LanguageAutocomplete(autocomplete.Select2ListView):
    def get_list(self):
        # Extract the display names from your LanguageField's choices
        choices = LanguageField().get_language_choices()
        return choices

    def get_queryset(self):
        # Return the choices for the languages
        return self.get_language_choices()


########
# Read #
########


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class ReadListView(ListView):
    template_name = "read/read_list.html"
    context_object_name = "objects"

    def get_queryset(self):
        book_content_type = ContentType.objects.get_for_model(Book)
        issue_content_type = ContentType.objects.get_for_model(Issue)
        recent_date = timezone.now() - timedelta(days=7)

        trending_books = (
            Book.objects.annotate(
                checkins=Count(
                    "readcheckin",
                    filter=Q(
                        readcheckin__content_type=book_content_type,
                        readcheckin__timestamp__gte=recent_date,
                    ),
                    distinct=True,
                ),
                latest_checkin=Max(
                    "readcheckin__timestamp",
                    filter=Q(
                        readcheckin__content_type=book_content_type,
                        readcheckin__timestamp__gte=recent_date,
                    ),
                ),
            )
            .exclude(checkins=0)
            .order_by("-latest_checkin")[:12]
        )

        trending_issues = (
            Issue.objects.annotate(
                checkins=Count(
                    "readcheckin",
                    filter=Q(
                        readcheckin__content_type=issue_content_type,
                        readcheckin__timestamp__gte=recent_date,
                    ),
                    distinct=True,
                ),
                latest_checkin=Max(
                    "readcheckin__timestamp",
                    filter=Q(
                        readcheckin__content_type=issue_content_type,
                        readcheckin__timestamp__gte=recent_date,
                    ),
                ),
            )
            .exclude(checkins=0)
            .order_by("-latest_checkin")[:12]
        )

        return {
            "recent_books": Book.objects.all().order_by("-created_at")[:12],
            "recent_issues": Issue.objects.all().order_by("-created_at")[:12],
            "trending_books": trending_books,
            "trending_issues": trending_issues,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["genres"] = (
            Genre.objects.filter(Q(read_works__isnull=False))
            .order_by("name")
            .distinct()
        )
        # Additional context for the statistics
        context["works_count"] = Work.objects.count()
        context["instances_count"] = Instance.objects.count()
        context["books_count"] = Book.objects.count()
        context["periodicals_count"] = Periodical.objects.count()
        context["issues_count"] = Issue.objects.count()
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class ReadListAllView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = "read/read_list_all.html"
    context_object_name = "objects"

    def test_func(self):
        # Only allow admin users
        return self.request.user.is_superuser

    def handle_no_permission(self):
        # If not allowed, raise a 404 error
        raise Http404

    def get_queryset(self):
        return {
            "books": Book.objects.all().order_by("-created_at"),
            "issues": Issue.objects.all().order_by("-created_at"),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["genres"] = (
            Genre.objects.filter(Q(read_works__isnull=False))
            .order_by("name")
            .distinct()
        )
        # Additional context for the statistics
        context["works_count"] = Work.objects.count()
        context["instances_count"] = Instance.objects.count()
        context["books_count"] = Book.objects.count()
        context["periodicals_count"] = Periodical.objects.count()
        context["issues_count"] = Issue.objects.count()
        return context


###########
# Checkin #
###########


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class ReadCheckInDetailView(DetailView):
    model = ReadCheckIn
    template_name = "read/read_checkin_detail.html"
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
                content_type="ReadCheckIn",
            )
        return HttpResponseRedirect(request.path_info)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = get_visible_comments(self.request.user, self.object)
        context["comment_form"] = CommentForm()
        context["repost_form"] = RepostForm(user=self.request.user)
        context["app_label"] = self.object._meta.app_label
        context["object_type"] = self.object._meta.model_name.lower()

        content_object = self.object.content_object

        context["publisher"] = get_company_name(
            [content_object.publisher], content_object.publication_date
        )[0]

        checkin_count = get_visible_checkins(
            request_user=self.request.user,
            content_type=ContentType.objects.get_for_model(content_object),
            object_id=content_object.id,
            CheckInModel=ReadCheckIn,
            checkin_user=self.object.user,
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


class ReadCheckInUpdateView(LoginRequiredMixin, UpdateView):
    model = ReadCheckIn
    form_class = ReadCheckInForm
    template_name = "read/read_checkin_update.html"

    def get_success_url(self):
        return reverse_lazy(
            "write:read_checkin_detail",
            kwargs={"pk": self.object.pk, "username": self.object.user.username},
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        content_type = ContentType.objects.get_for_model(Book)
        context["checkin_form"] = ReadCheckInForm(
            initial={
                "content_type": content_type.id,
                "object_id": self.object.id,
                "user": self.request.user.id,
                "visibility": self.object.visibility,
            }
        )
        return context


class ReadCheckInDeleteView(LoginRequiredMixin, DeleteView):
    model = ReadCheckIn
    template_name = "read/read_checkin_delete.html"

    def get_success_url(self):
        content_object = self.object.content_object

        if isinstance(content_object, Book):
            return reverse_lazy(
                "read:book_detail",
                kwargs={
                    "pk": self.object.content_object.pk,
                },
            )
        elif isinstance(content_object, Issue):
            return reverse_lazy(
                "read:issue_detail",
                kwargs={
                    "pk": self.object.content_object.pk,
                    "periodical_id": self.object.content_object.periodical.pk,
                },
            )
        else:
            return reverse_lazy("home")


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class GenericCheckInListView(ListView):
    """
    All check-ins from a given user for a book or an issue.
    """

    model = ReadCheckIn
    template_name = "read/read_checkin_list.html"
    context_object_name = "checkins"

    def get_model(self):
        if self.kwargs["model_name"] == "book":
            return Book
        elif self.kwargs["model_name"] == "issue":
            return Issue
        else:
            return None

    def get_queryset(self):
        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        status = self.request.GET.get("status", "")
        profile_user = get_object_or_404(
            User, username=self.kwargs["username"]
        )  # Get user from url param
        model = self.get_model()
        if model is None:
            checkins = ReadCheckIn.objects.none()
        else:
            content_type = ContentType.objects.get_for_model(model)
            object_id = self.kwargs["object_id"]  # Get object id from url param
            checkins = ReadCheckIn.objects.filter(
                user=profile_user, content_type=content_type, object_id=object_id
            )

            if self.request.user.is_authenticated:
                checkins = checkins.filter(
                    Q(visibility="PU") | Q(visible_to=self.request.user)
                )
            else:
                checkins = checkins.filter(visibility="PU")

        if status:
            if status == "read_reread":
                checkins = checkins.filter(
                    Q(status="finished_reading") | Q(status="reread")
                )
            elif status == "reading_rereading":
                checkins = checkins.filter(Q(status="reading") | Q(status="rereading"))
            else:
                checkins = checkins.filter(status=status)

        return checkins.order_by(order)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        status = self.request.GET.get("status", "")  # Added status
        profile_user = get_object_or_404(User, username=self.kwargs["username"])
        context["profile_user"] = profile_user
        context["order"] = order
        context["status"] = status  # Add status to context

        model = self.get_model()
        if model is None:
            context["checkins"] = ReadCheckIn.objects.none()
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

            if content_type.model == "book":
                book = get_object_or_404(Book, pk=object_id)
                roles = {}
                for book_role in book.bookrole_set.all():
                    if book_role.role.name not in roles:
                        roles[book_role.role.name] = []
                    alt_name_or_creator_name = (
                        book_role.alt_name or book_role.creator.name
                    )
                    roles[book_role.role.name].append(
                        (book_role.creator, alt_name_or_creator_name)
                    )
                context["roles"] = roles
                context["publisher"] = get_company_name(
                    [book.publisher], book.publication_date
                )[0]

        context["model_name"] = self.kwargs.get("model_name", "book")

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
    """
    All latest check-ins from all users of a book or an issue.
    """

    model = ReadCheckIn
    template_name = "read/read_checkin_list_all.html"
    context_object_name = "checkins"
    paginate_by = 25

    def get_model(self):
        if self.kwargs["model_name"] == "book":
            return Book
        elif self.kwargs["model_name"] == "issue":
            return Issue
        else:
            return None

    def get_queryset(self):
        model = self.get_model()
        if model is None:
            return ReadCheckIn.objects.none()

        content_type = ContentType.objects.get_for_model(model)
        object_id = self.kwargs["object_id"]  # Get object id from url param

        latest_checkin_subquery = (
            get_visible_checkins(
                self.request.user, ReadCheckIn, content_type, object_id
            )
            .filter(user=OuterRef("user"))
            .order_by("-timestamp")
        )

        checkins = (
            get_visible_checkins(
                self.request.user, ReadCheckIn, content_type, object_id
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
            if status == "read_reread":
                checkins = checkins.filter(
                    Q(status="finished_reading") | Q(status="reread")
                )
            elif status == "reading_rereading":
                checkins = checkins.filter(Q(status="reading") | Q(status="rereading"))
            else:
                checkins = checkins.filter(status=status)

        user_checkin_counts = (
            get_visible_checkins(
                self.request.user, ReadCheckIn, content_type, object_id
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
        content_type = ContentType.objects.get_for_model(model)
        if model is not None:
            context["object"] = model.objects.get(
                pk=self.kwargs["object_id"]
            )  # Get the object details

            if content_type.model == "book":
                book = get_object_or_404(Book, pk=self.kwargs["object_id"])
                roles = {}
                for book_role in book.bookrole_set.all():
                    if book_role.role.name not in roles:
                        roles[book_role.role.name] = []
                    alt_name_or_creator_name = (
                        book_role.alt_name or book_role.creator.name
                    )
                    roles[book_role.role.name].append(
                        (book_role.creator, alt_name_or_creator_name)
                    )
                context["roles"] = roles
                context["publisher"] = get_company_name(
                    [book.publisher], book.publication_date
                )[0]

        context["order"] = self.request.GET.get(
            "order", "-timestamp"
        )  # Default is '-timestamp'

        context["status"] = self.request.GET.get("status", "")
        context["model_name"] = self.kwargs.get("model_name", "book")

        include_mathjax, include_mermaid = check_required_js(context["page_obj"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        return context


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
class GenericCheckInUserListView(ListView):
    """
    All latest check-ins from a given user of all books and issues.
    """

    model = ReadCheckIn
    template_name = "read/read_checkin_list_user.html"
    context_object_name = "checkins"
    paginate_by = 25

    def get_queryset(self):
        profile_user = get_object_or_404(User, username=self.kwargs["username"])

        latest_checkin_subquery = get_visible_checkins(
            self.request.user,
            ReadCheckIn,
            OuterRef("content_type"),
            OuterRef("object_id"),
            checkin_user=profile_user,
        ).order_by("-timestamp")

        checkins = (
            ReadCheckIn.objects.filter(user=profile_user)
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
            if status == "read_reread":
                checkins = checkins.filter(
                    Q(status="finished_reading") | Q(status="reread")
                )
            elif status == "reading_rereading":
                checkins = checkins.filter(Q(status="reading") | Q(status="rereading"))
            else:
                checkins = checkins.filter(status=status)

        # Adding count of check-ins for each book or issue
        user_checkin_counts = (
            get_visible_checkins(
                self.request.user,
                ReadCheckIn,
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
            checkin.publisher = get_company_name(
                [checkin.content_object.publisher],
                checkin.content_object.publication_date,
            )[0]

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


class BookSeriesCreateView(LoginRequiredMixin, CreateView):
    model = BookSeries
    form_class = BookSeriesForm
    template_name = "read/series_create.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["books"] = BookInSeriesFormSet(self.request.POST)
        else:
            data["books"] = BookInSeriesFormSet(queryset=BookInSeries.objects.none())
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        books = context["books"]

        if books.is_valid():
            with transaction.atomic():
                form.instance.created_by = self.request.user
                self.object = form.save()
                books.instance = self.object
                books.save()
        else:
            return self.form_invalid(
                form
            )  # If there are formset errors, re-render the form.
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class BookSeriesDetailView(DetailView):
    model = BookSeries
    template_name = "read/series_detail.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # contributors
        context["contributors"] = get_contributors(self.object)

        return context


class BookSeriesUpdateView(LoginRequiredMixin, UpdateView):
    model = BookSeries
    form_class = BookSeriesForm
    template_name = "read/series_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["books"] = BookInSeriesFormSet(self.request.POST, instance=self.object)
        else:
            data["books"] = BookInSeriesFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        books = context["books"]

        if books.is_valid():
            self.object = form.save()
            books.instance = self.object
            books.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("read:series_detail", kwargs={"pk": self.object.pk})


#########
# Genre #
#########
@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class GenreDetailView(DetailView):
    model = Genre
    template_name = "read/genre_detail.html"  # Update with your actual template name
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the genre object
        genre = self.object
        works = Work.objects.filter(genres=genre).order_by("-publication_date")

        works_with_authors = []
        for work in works:
            authors = Creator.objects.filter(
                read_workrole_set__work=work,
                read_workrole_set__role__name__in=[
                    "Author",
                    "Story By",
                    "Novelization By",
                ],
            )
            work.authors = authors
            works_with_authors.append(work)

        context["works"] = works_with_authors

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
class InstanceHistoryView(HistoryViewMixin, DetailView):
    model = Instance
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class IssueHistoryView(HistoryViewMixin, DetailView):
    model = Issue
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class PeriodicalHistoryView(HistoryViewMixin, DetailView):
    model = Periodical
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class BookHistoryView(HistoryViewMixin, DetailView):
    model = Book
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class BookSeriesHistoryView(HistoryViewMixin, DetailView):
    model = BookSeries
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


##############
# Book Group #
##############


class BookGroupCreateView(LoginRequiredMixin, CreateView):
    model = BookGroup
    form_class = BookGroupForm
    template_name = "read/bookgroup_create.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["books"] = BookInGroupFormSet(self.request.POST)
        else:
            data["books"] = BookInGroupFormSet(queryset=BookInGroup.objects.none())
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        books = context["books"]

        print("Formset data before validation:", books.data)  # Debugging print

        if books.is_valid():
            print("Formset cleaned_data:", books.cleaned_data)  # Debugging print
            with transaction.atomic():
                form.instance.created_by = self.request.user
                self.object = form.save()
                books.instance = self.object
                books.save()
        else:
            print("Formset errors:", books.errors)  # Debugging print
            return self.form_invalid(
                form
            )  # If there are formset errors, re-render the form.
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class BookGroupDetailView(DetailView):
    model = BookGroup
    template_name = "read/bookgroup_detail.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Get contributors
        context["contributors"] = get_contributors(self.object)

        # Custom sorting logic for book by date completeness
        # First, fetch all related book
        books = self.object.bookingroup_set.all()

        # Then, sort them by their 'publication_date' field length and value
        books = books.annotate(
            date_length=Length("book__publication_date"),
            padded_date=F("book__publication_date"),
        ).order_by("-date_length", "padded_date")

        for book_in_group in books:
            print(book_in_group.book.publisher)
            book_in_group.publisher = get_company_name(
                [book_in_group.book.publisher], book_in_group.book.publication_date
            )[0]

        # Update the context with the sorted book
        context["sorted_books"] = books
        if books:
            context["oldest_book"] = books.first()

        return context


class BookGroupUpdateView(LoginRequiredMixin, UpdateView):
    model = BookGroup
    form_class = BookGroupForm
    template_name = "read/bookgroup_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["books"] = BookInGroupFormSet(self.request.POST, instance=self.object)
        else:
            data["books"] = BookInGroupFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        books = context["books"]

        print(
            "Formset data before validation for updating:", books.data
        )  # Debugging print

        if books.is_valid():
            print(
                "Formset cleaned_data for updating:", books.cleaned_data
            )  # Debugging print
            self.object = form.save()
            books.instance = self.object
            books.save()
        else:
            print("Formset errors:", books.errors)  # Print out the formset errors.
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("read:bookgroup_detail", kwargs={"pk": self.object.pk})


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class BookGroupHistoryView(HistoryViewMixin, DetailView):
    model = BookGroup
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context
