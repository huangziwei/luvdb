from datetime import timedelta
from typing import Any

from dal import autocomplete
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count, F, Max, OuterRef, Q, Subquery
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.html import format_html
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from activity_feed.models import Block
from discover.views import user_has_upvoted
from entity.models import LanguageField
from entity.views import HistoryViewMixin
from watch.models import Movie, Series
from write.forms import CommentForm, RepostForm
from write.models import Comment, ContentInList

from .forms import (
    BookForm,
    BookInSeriesFormSet,
    BookInstanceFormSet,
    BookRoleFormSet,
    BookSeriesForm,
    InstanceForm,
    InstanceRoleFormSet,
    IssueForm,
    IssueInstanceFormSet,
    PeriodicalForm,
    ReadCheckInForm,
    WorkForm,
    WorkRoleFormSet,
)
from .models import (
    Book,
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

            def sorting_key(item):
                if item.type == "audiobook":
                    return item.release_date
                return item.publication_date

            items = sorted(
                list(books) + list(issues) + list(audiobooks), key=sorting_key
            )
            language_grouped_instances[lang].append(
                {"instance": instance, "items": items}
            )

        context["grouped_instances"] = language_grouped_instances

        def get_adaptation_release_date(adaptation):
            if isinstance(adaptation, Movie):
                # Assuming you want to take the earliest release date for each movie
                regional_dates = adaptation.region_release_dates.all().order_by(
                    "release_date"
                )
                return regional_dates[0].release_date if regional_dates else None
            elif isinstance(adaptation, Series):
                return adaptation.release_date
            else:
                return None

        adaptations = list(Movie.objects.filter(based_on=self.object)) + list(
            Series.objects.filter(based_on=self.object)
        )
        adaptations.sort(key=lambda x: get_adaptation_release_date(x))
        context["adaptations"] = adaptations

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
        unique_usernames = {
            record.history_user
            for record in self.object.history.all()
            if record.history_user is not None
        }
        context["contributors"] = unique_usernames

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


class InstanceDetailView(DetailView):
    model = Instance
    template_name = "read/instance_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        grouped_roles = {}
        for role in self.object.instancerole_set.all():
            if role.role.name not in grouped_roles:
                grouped_roles[role.role.name] = []
            alt_name_or_creator_name = role.alt_name or role.creator.name
            grouped_roles[role.role.name].append(
                (role.creator, alt_name_or_creator_name)
            )
        context["grouped_roles"] = grouped_roles
        context["books"] = self.object.books.all().order_by("publication_date")
        context["issues"] = self.object.issues.all().order_by("publication_date")
        context["audiobooks"] = self.object.audiobooks.all().order_by("release_date")

        # contributors
        unique_usernames = {
            record.history_user
            for record in self.object.history.all()
            if record.history_user is not None
        }
        context["contributors"] = unique_usernames
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


class BookDetailView(DetailView):
    model = Book
    template_name = "read/book_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        book = get_object_or_404(Book, pk=self.kwargs["pk"])

        main_role_names = [
            "Author",
            "Translator",
            "Editor",
            "Created By",
            "Novelization By",
            "Ghost Writer",
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
            }
        )

        # Fetch the latest check-in from each user.
        latest_checkin_subquery = ReadCheckIn.objects.filter(
            content_type=content_type.id,
            object_id=self.object.id,
            user=OuterRef("user"),
        ).order_by("-timestamp")
        checkins = (
            ReadCheckIn.objects.filter(
                content_type=content_type.id, object_id=self.object.id
            )
            .annotate(
                latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
            )
            .filter(timestamp=F("latest_checkin"))
        ).order_by("-timestamp")[:5]

        context["checkins"] = checkins

        user_checkin_counts = (
            ReadCheckIn.objects.filter(
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

        # Book check-in status counts, considering only latest check-in per user
        latest_checkin_status_subquery = (
            ReadCheckIn.objects.filter(
                content_type=content_type.id,
                object_id=self.object.id,
                user=OuterRef("user"),
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
            else:
                context["latest_user_status"] = "to_read"
        else:
            context["latest_user_status"] = "to_read"

        # contributors
        unique_usernames = {record.history_user for record in book.history.all()}
        context["contributors"] = unique_usernames

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


class PeriodicalDetailView(DetailView):
    model = Periodical
    template_name = "read/periodical_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # contributors
        unique_usernames = {
            record.history_user
            for record in self.object.history.all()
            if record.history_user is not None
        }
        context["contributors"] = unique_usernames
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
        latest_checkin_subquery = ReadCheckIn.objects.filter(
            content_type=content_type.id,
            object_id=self.object.id,
            user=OuterRef("user"),
        ).order_by("-timestamp")
        checkins = (
            ReadCheckIn.objects.filter(
                content_type=content_type.id, object_id=self.object.id
            )
            .annotate(
                latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
            )
            .filter(timestamp=F("latest_checkin"))
        ).order_by("-timestamp")[:5]

        # Get the count of check-ins for each user for this series
        user_checkin_counts = (
            ReadCheckIn.objects.filter(
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
        for checkin in checkins:
            checkin.total_checkins = user_checkin_count_dict.get(
                checkin.user.username, 0
            )

        # Issue check-in status counts, considering only latest check-in per user
        latest_checkin_status_subquery = (
            ReadCheckIn.objects.filter(
                content_type=content_type.id,
                object_id=self.object.id,
                user=OuterRef("user"),
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

        # contributors
        unique_usernames = {
            record.history_user
            for record in self.object.history.all()
            if record.history_user is not None
        }
        context["contributors"] = unique_usernames

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
            label = format_html(
                "{} ({} - {})", item.title, author_name, publication_year
            )
        else:
            label = format_html("{} ({})", item.title, publication_year)

        return label


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
            label = format_html(
                "{} ({} - {})", item.title, author_name, publication_year
            )
        else:
            label = format_html("{} ({})", item.title, publication_year)

        return label


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


class ReadListAllView(ListView):
    template_name = "read/read_list_all.html"
    context_object_name = "objects"

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


class ReadCheckInDetailView(DetailView):
    model = ReadCheckIn
    template_name = "read/read_checkin_detail.html"
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

        checkin_count = ReadCheckIn.objects.filter(
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
            context[
                "checkins"
            ] = self.get_queryset()  # Use the queryset method to handle status filter
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

        context["model_name"] = self.kwargs.get("model_name", "book")

        return context


class GenericCheckInAllListView(ListView):
    """
    All latest check-ins from all users of a book or an issue.
    """

    model = ReadCheckIn
    template_name = "read/read_checkin_list_all.html"
    context_object_name = "checkins"

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

        latest_checkin_subquery = ReadCheckIn.objects.filter(
            content_type=content_type, object_id=object_id, user=OuterRef("user")
        ).order_by("-timestamp")

        checkins = (
            ReadCheckIn.objects.filter(content_type=content_type, object_id=object_id)
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
            ReadCheckIn.objects.filter(content_type=content_type, object_id=object_id)
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

        context["order"] = self.request.GET.get(
            "order", "-timestamp"
        )  # Default is '-timestamp'

        context["status"] = self.request.GET.get("status", "")
        context["model_name"] = self.kwargs.get("model_name", "book")

        return context


class GenericCheckInUserListView(ListView):
    """
    All latest check-ins from a given user of all books and issues.
    """

    model = ReadCheckIn
    template_name = "read/read_checkin_list_user.html"
    context_object_name = "checkins"

    def get_queryset(self):
        profile_user = get_object_or_404(User, username=self.kwargs["username"])

        latest_checkin_subquery = ReadCheckIn.objects.filter(
            user=profile_user,
            content_type=OuterRef("content_type"),
            object_id=OuterRef("object_id"),
        ).order_by("-timestamp")

        checkins = (
            ReadCheckIn.objects.filter(user=profile_user)
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

        # Adding count of check-ins for each book or issue
        user_checkin_counts = (
            ReadCheckIn.objects.filter(user=profile_user)
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

        context["order"] = self.request.GET.get(
            "order", "-timestamp"
        )  # Default is '-timestamp'

        context["status"] = self.request.GET.get("status", "")

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


class BookSeriesDetailView(DetailView):
    model = BookSeries
    template_name = "read/series_detail.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # contributors
        unique_usernames = {
            record.history_user
            for record in self.object.history.all()
            if record.history_user is not None
        }
        context["contributors"] = unique_usernames
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
                    "Created By",
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


class WorkHistoryView(HistoryViewMixin, DetailView):
    model = Work
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


class InstanceHistoryView(HistoryViewMixin, DetailView):
    model = Instance
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


class IssueHistoryView(HistoryViewMixin, DetailView):
    model = Issue
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


class PeriodicalHistoryView(HistoryViewMixin, DetailView):
    model = Periodical
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


class BookHistoryView(HistoryViewMixin, DetailView):
    model = Book
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context


class BookSeriesHistoryView(HistoryViewMixin, DetailView):
    model = BookSeries
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        context["history_data"] = self.get_history_data(object)
        return context
