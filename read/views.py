from dal import autocomplete
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView

from .forms import (
    BookForm,
    BookRoleFormSet,
    BookWork,
    BookWorkFormSet,
    WorkForm,
    WorkRoleFormSet,
)
from .models import Book, Publisher, Role, Work

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
            data["bookworks"] = BookWorkFormSet(
                self.request.POST, instance=self.object
            )  # Added this line
        else:
            data["bookroles"] = BookRoleFormSet(instance=self.object)
            data["bookworks"] = BookWorkFormSet(instance=self.object)  # And this line
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        bookroles = context["bookroles"]
        bookworks = context["bookworks"]  # Added this line
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if bookroles.is_valid():
                bookroles.instance = self.object
                bookroles.save()
            if bookworks.is_valid():  # And these lines
                bookworks.instance = self.object
                bookworks.save()
        return super().form_valid(form)


class BookDetailView(DetailView):
    model = Book
    template_name = "read/book_detail.html"


import logging

logger = logging.getLogger(__name__)


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
            data["bookworks"] = BookWorkFormSet(self.request.POST, instance=self.object)
        else:
            data["bookroles"] = BookRoleFormSet(instance=self.object)
            data["bookworks"] = BookWorkFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        bookroles = context["bookroles"]
        bookworks = context["bookworks"]
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
                    if bookworks.is_valid():
                        bookworks.instance = self.object
                        bookworks.save()
                    else:
                        logger.error(
                            f"BookWorks formset is not valid: {bookworks.errors}"
                        )

        return super().form_valid(form)


class WorkAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Work.objects.none()

        qs = Work.objects.all()

        if self.q:
            qs = qs.filter(title__istartswith=self.q)

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
