from dal import autocomplete
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
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

from write.forms import CommentForm, RepostForm
from write.models import Comment

from .forms import (
    BookForm,
    BookInSeriesFormSet,
    BookInstanceForm,
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
    BookSeries,
    Instance,
    Issue,
    LanguageField,
    Periodical,
    Person,
    Publisher,
    ReadCheckIn,
    Role,
    Work,
)

User = get_user_model()

#############
# Publisher #
#############


class PublisherCreateView(LoginRequiredMixin, CreateView):
    model = Publisher
    fields = [
        "name",
        "romanized_name",
        "history",
        "location",
        "website",
        "founded_date",
        "closed_date",
    ]
    template_name = "read/publisher_create.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("read:publisher_detail", kwargs={"pk": self.object.pk})


class PublisherDetailView(DetailView):
    model = Publisher
    template_name = "read/publisher_detail.html"


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
        return reverse_lazy("read:work_detail", kwargs={"pk": self.object.pk})


class WorkDetailView(DetailView):
    model = Work
    template_name = "read/work_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        work = get_object_or_404(Work, pk=self.kwargs.get("pk"))
        instances = work.instances.all().order_by("publication_date")
        context["instances"] = []
        for instance in instances:
            books = instance.books.all()
            for book in books:
                book.type = "book"
            issues = instance.issues.all()
            for issue in issues:
                issue.type = "issue"
            items = sorted(list(books) + list(issues), key=lambda x: x.publication_date)
            context["instances"].append({"instance": instance, "items": items})
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
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if instanceroles.is_valid():
                instanceroles.instance = self.object
                instanceroles.save()
            else:
                print(instanceroles.errors)  # print out formset errors
        return super().form_valid(form)


class InstanceUpdateView(LoginRequiredMixin, UpdateView):
    model = Instance
    form_class = InstanceForm
    template_name = "read/instance_update.html"

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
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if instanceroles.is_valid():
                instanceroles.instance = self.object
                instanceroles.save()
            else:
                print(instanceroles.errors)  # print out formset errors
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("read:instance_detail", kwargs={"pk": self.object.pk})


class InstanceDetailView(DetailView):
    model = Instance
    template_name = "read/instance_detail.html"


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

        roles = {}
        for book_role in book.bookrole_set.all():
            if book_role.role.name not in roles:
                roles[book_role.role.name] = []
            alt_name_or_person_name = book_role.alt_name or book_role.person.name
            roles[book_role.role.name].append(
                (book_role.person, alt_name_or_person_name)
            )
        context["roles"] = roles

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
        else:
            print("read_checkin_in_detail:", form.errors)

        return redirect(self.object.get_absolute_url())


class BookUpdateView(UpdateView):
    model = Book
    form_class = BookForm
    template_name = "read/book_update.html"

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
        with transaction.atomic():
            form.instance.updated_by = self.request.user
            if self.request.method == "POST":
                form = BookForm(
                    self.request.POST, self.request.FILES, instance=self.object
                )
                if form.is_valid():
                    self.object = form.save()
                    if bookroles.is_valid():
                        bookroles.instance = self.object
                        bookroles.save()
                    else:
                        print(
                            "BookRoles form errors: ", bookroles.errors
                        )  # print form errors
                    if bookinstances.is_valid():
                        bookinstances.instance = self.object
                        bookinstances.save()

        return super().form_valid(form)


class PeriodicalCreateView(CreateView):
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


class PeriodicalUpdateView(UpdateView):
    model = Periodical
    form_class = PeriodicalForm
    template_name = "read/periodical_update.html"

    def get_success_url(self):
        return reverse_lazy("read:periodical_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class IssueCreateView(CreateView):
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
        return reverse("read:periodical_detail", kwargs={"pk": periodical_id})

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
            else:
                print(issueinstances.errors)  # print out formset errors
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

        context["checkins"] = checkins

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
        else:
            print("read_checkin_in_detail:", form.errors)

        return redirect(self.object.get_absolute_url())


class IssueUpdateView(UpdateView):
    model = Issue
    form_class = IssueForm
    template_name = "read/periodical_issue_update.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["periodical"].disabled = True
        return form

    def get_success_url(self):
        periodical_id = self.object.periodical.pk
        return reverse("read:periodical_detail", kwargs={"pk": periodical_id})

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
            else:
                print(issueinstances.errors)  # print out formset errors
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
            authors = Person.objects.filter(name__istartswith=self.q)

            # get the author role
            author_role = Role.objects.filter(name="Author").first()

            # get all the works which are associated with these authors
            qs = qs.filter(
                Q(workrole__role=author_role, workrole__person__in=authors)
                | Q(title__icontains=self.q)
                | Q(publication_date__icontains=self.q)
            )

        return qs[:10]

    def get_result_label(self, item):
        # Get the first person with a role of 'Author' for the book
        author_role = Role.objects.filter(
            name="Author"
        ).first()  # Adjust 'Author' to match your data
        work_role = item.workrole_set.filter(role=author_role).first()
        author_name = (
            work_role.person.name if work_role and work_role.person else "Unknown"
        )

        # Get the year from the publication_date
        publication_year = (
            item.publication_date[:4] if item.publication_date else "Unknown"
        )

        # Format the label
        label = format_html("{} ({}, {})", item.title, author_name, publication_year)

        return label


class InstanceAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Instance.objects.none()

        qs = Instance.objects.all()

        if self.q:
            # get all the authors whose name starts with query
            authors = Person.objects.filter(name__istartswith=self.q)

            # get the author role
            author_role = Role.objects.filter(name="Author").first()

            # get all the instances which are associated with these authors
            qs = qs.filter(
                Q(instancerole__role=author_role, instancerole__person__in=authors)
                | Q(title__icontains=self.q)
                | Q(publication_date__icontains=self.q)
            )

        return qs[:10]

    def get_result_label(self, item):
        # Get the first person with a role of 'Author' for the book
        author_role = Role.objects.filter(
            name="Author"
        ).first()  # Adjust 'Author' to match your data
        instance_role = item.instancerole_set.filter(role=author_role).first()
        author_name = (
            instance_role.alt_name
            if instance_role and instance_role.alt_name
            else instance_role.person.name
        )

        # Get the year from the publication_date
        publication_year = (
            item.publication_date[:4] if item.publication_date else "Unknown"
        )

        # Format the label
        label = format_html("{} ({}, {})", item.title, author_name, publication_year)

        return label


class PublisherAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Publisher.objects.none()

        qs = Publisher.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


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
        return {
            "recent_books": Book.objects.all().order_by("-created_at")[:12],
            "recent_issues": Issue.objects.all().order_by("-created_at")[:12],
        }


###########
# Checkin #
###########


class ReadCheckInCreateView(LoginRequiredMixin, CreateView):
    model = ReadCheckIn
    form_class = ReadCheckInForm
    template_name = "read/checkin_create.html"

    def form_valid(self, form):
        book = get_object_or_404(
            Book, pk=self.kwargs.get("book_id")
        )  # Fetch the book based on URL parameter
        form.instance.book = book
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("read:read_checkin_detail", kwargs={"pk": self.object.pk})


class ReadCheckInDetailView(DetailView):
    model = ReadCheckIn
    template_name = "read/read_checkin_detail.html"
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


class ReadCheckInUpdateView(LoginRequiredMixin, UpdateView):
    model = ReadCheckIn
    form_class = ReadCheckInForm
    template_name = "read/read_checkin_update.html"

    def get_success_url(self):
        return reverse_lazy("read:read_checkin_detail", kwargs={"pk": self.object.pk})


class ReadCheckInDeleteView(LoginRequiredMixin, DeleteView):
    model = ReadCheckIn
    template_name = "read/read_checkin_delete.html"

    def get_success_url(self):
        return reverse_lazy(
            "read:book_detail", kwargs={"pk": self.object.content_object.pk}
        )


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
        status = self.request.GET.get("status")
        user = get_object_or_404(
            User, username=self.kwargs["username"]
        )  # Get user from url param
        model = self.get_model()
        if model is None:
            checkins = ReadCheckIn.objects.none()
        else:
            content_type = ContentType.objects.get_for_model(model)
            object_id = self.kwargs["object_id"]  # Get object id from url param
            checkins = ReadCheckIn.objects.filter(
                user=user, content_type=content_type, object_id=object_id
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
        status = self.request.GET.get("status")  # Added status
        user = get_object_or_404(User, username=self.kwargs["username"])
        context["user"] = user
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

        status = self.request.GET.get("status")
        if status:
            if status == "read_reread":
                checkins = checkins.filter(
                    Q(status="finished_reading") | Q(status="reread")
                )
            elif status == "reading_rereading":
                checkins = checkins.filter(Q(status="reading") | Q(status="rereading"))
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
        user = get_object_or_404(User, username=self.kwargs["username"])

        latest_checkin_subquery = ReadCheckIn.objects.filter(
            user=user,
            content_type=OuterRef("content_type"),
            object_id=OuterRef("object_id"),
        ).order_by("-timestamp")

        checkins = (
            ReadCheckIn.objects.filter(user=user)
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
            if status == "read_reread":
                checkins = checkins.filter(
                    Q(status="finished_reading") | Q(status="reread")
                )
            elif status == "reading_rereading":
                checkins = checkins.filter(Q(status="reading") | Q(status="rereading"))
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


class BookSeriesCreateView(LoginRequiredMixin, CreateView):
    model = BookSeries
    form_class = BookSeriesForm
    template_name = "read/series_create.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["books"] = BookInSeriesFormSet(self.request.POST)
        else:
            data["books"] = BookInSeriesFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        books = context["books"]
        with transaction.atomic():
            form.instance.created_by = self.request.user
            self.object = form.save()
            if books.is_valid():
                books.instance = self.object
                books.save()
        return super().form_valid(form)


class BookSeriesDetailView(DetailView):
    model = BookSeries
    template_name = "read/series_detail.html"  # Update this


class BookSeriesUpdateView(LoginRequiredMixin, UpdateView):
    model = BookSeries
    form_class = BookSeriesForm
    template_name = "read/series_update.html"

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
        else:
            print("Formset errors:", books.errors)  # Print out the formset errors.
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("read:series_detail", kwargs={"pk": self.object.pk})
