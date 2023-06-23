from dal import autocomplete
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count, F, Max, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
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
    BookCheckInForm,
    BookForm,
    BookRoleFormSet,
    BookWorkRoleForm,
    BookWorkRoleFormSet,
    WorkForm,
    WorkRoleFormSet,
)
from .models import Book, BookCheckIn, Person, Publisher, Role, Work

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
            data["bookworkroles"] = BookWorkRoleFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["bookroles"] = BookRoleFormSet(instance=self.object)
            data["bookworkroles"] = BookWorkRoleFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        bookroles = context["bookroles"]
        bookworkroles = context["bookworkroles"]
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if bookroles.is_valid():
                bookroles.instance = self.object
                bookroles.save()
            if bookworkroles.is_valid():
                bookworkroles.instance = self.object
                bookworkroles.save()
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
        context["checkin_form"] = BookCheckInForm(
            initial={"book": self.object, "author": self.request.user}
        )

        # Fetch the latest check-in from each user.
        latest_checkin_subquery = BookCheckIn.objects.filter(
            book=self.object, author=OuterRef("author")
        ).order_by("-timestamp")
        checkins = (
            BookCheckIn.objects.filter(book=self.object)
            .annotate(
                latest_checkin=Subquery(latest_checkin_subquery.values("timestamp")[:1])
            )
            .filter(timestamp=F("latest_checkin"))
        ).order_by("-timestamp")[:5]

        context["checkins"] = checkins

        # Book check-in status counts, considering only latest check-in per user
        latest_checkin_status_subquery = (
            BookCheckIn.objects.filter(book=self.object, author=OuterRef("author"))
            .order_by("-timestamp")
            .values("status")[:1]
        )
        latest_checkins = (
            BookCheckIn.objects.filter(book=self.object)
            .annotate(latest_checkin_status=Subquery(latest_checkin_status_subquery))
            .values("author", "latest_checkin_status")
            .distinct()
        )

        to_read_count = sum(
            1 for item in latest_checkins if item["latest_checkin_status"] == "to_read"
        )
        reading_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"] in ["currently_reading", "rereading"]
        )
        read_count = sum(
            1
            for item in latest_checkins
            if item["latest_checkin_status"]
            in ["finished_reading", "finished_rereading"]
        )

        # Add status counts to context
        context.update(
            {
                "to_read_count": to_read_count,
                "reading_count": reading_count,
                "read_count": read_count,
            }
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
        form = BookCheckInForm(
            data=request.POST,
            initial={
                "book": self.object,
                "author": request.user,
                "comments_enabled": True,
            },
        )
        if form.is_valid():
            book_check_in = form.save(commit=False)
            book_check_in.author = request.user  # Set the author manually here
            book_check_in.save()
        else:
            print(form.errors)

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
            data["bookworkroles"] = BookWorkRoleFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["bookroles"] = BookRoleFormSet(instance=self.object)
            data["bookworkroles"] = BookWorkRoleFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        bookroles = context["bookroles"]
        print("bookroles: ", bookroles.errors)
        bookworkroles = context["bookworkroles"]
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
                    if bookworkroles.is_valid():
                        bookworkroles.instance = self.object
                        bookworkroles.save()

        return super().form_valid(form)


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
            qs = qs.filter(workrole__role=author_role, workrole__person__in=authors)

        return qs

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


class PublisherAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Publisher.objects.none()

        qs = Publisher.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


########
# Read #
########


class ReadListView(ListView):
    template_name = "read/read_list.html"
    context_object_name = "objects"

    def get_queryset(self):
        recent_works = Work.objects.all().order_by("-created_at")[:10]
        for work in recent_works:
            authors = work.workrole_set.filter(role__name="Author")
            work.authors = ", ".join(str(author.person) for author in authors)
        return {
            "recent_books": Book.objects.all().order_by("-created_at")[:10],
            "recent_works": recent_works,
            "recent_persons": Person.objects.all().order_by("-created_at")[:10],
        }


###########
# Checkin #
###########


class BookCheckInCreateView(LoginRequiredMixin, CreateView):
    model = BookCheckIn
    form_class = BookCheckInForm
    template_name = "read/checkin_create.html"

    def form_valid(self, form):
        book = get_object_or_404(
            Book, pk=self.kwargs.get("book_id")
        )  # Fetch the book based on URL parameter
        form.instance.book = book
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("read:book_checkin_detail", kwargs={"pk": self.object.pk})


class BookCheckInDetailView(DetailView):
    model = BookCheckIn
    template_name = "read/book_checkin_detail.html"
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


class BookCheckInUpdateView(LoginRequiredMixin, UpdateView):
    model = BookCheckIn
    form_class = BookCheckInForm
    template_name = "read/book_checkin_update.html"

    def get_success_url(self):
        return reverse_lazy("read:book_checkin_detail", kwargs={"pk": self.object.pk})


class BookCheckInDeleteView(LoginRequiredMixin, DeleteView):
    model = BookCheckIn
    template_name = "read/book_checkin_delete.html"

    def get_success_url(self):
        return reverse_lazy("read:book_detail", kwargs={"pk": self.object.book.pk})


class BookCheckInListView(ListView):
    model = BookCheckIn
    template_name = "read/book_checkin_list.html"
    context_object_name = "checkins"

    def get_queryset(self):
        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        user = get_object_or_404(
            User, username=self.kwargs["username"]
        )  # Get user from url param
        book_id = self.kwargs["book_id"]  # Get book id from url param
        return BookCheckIn.objects.filter(author=user, book__id=book_id).order_by(order)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super().get_context_data(**kwargs)

        order = self.request.GET.get("order", "-timestamp")  # Default is '-timestamp'
        user = get_object_or_404(User, username=self.kwargs["username"])
        context["user"] = user
        context["order"] = order
        context["checkins"] = BookCheckIn.objects.filter(
            author__username=self.kwargs["username"], book__id=self.kwargs["book_id"]
        ).order_by(order)
        # Get the book details
        context["book"] = get_object_or_404(Book, pk=self.kwargs["book_id"])
        return context


class BookCheckInAllListView(ListView):
    model = BookCheckIn
    template_name = "read/book_checkin_list_all.html"
    context_object_name = "checkins"

    def get_queryset(self):
        # Fetch the latest check-in from each user.
        latest_checkin_subquery = BookCheckIn.objects.filter(
            book=self.kwargs["book_id"], author=OuterRef("author")
        ).order_by("-timestamp")

        checkins = (
            BookCheckIn.objects.filter(book=self.kwargs["book_id"])
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

        return checkins

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super().get_context_data(**kwargs)

        # Get the book details
        context["book"] = get_object_or_404(Book, pk=self.kwargs["book_id"])
        context["order"] = self.request.GET.get(
            "order", "-timestamp"
        )  # Default is '-timestamp'
        return context
