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
    EditionForm,
    EditionRoleFormSet,
    PersonForm,
)
from .models import Book, Edition, Person, Publisher, Role

##########
# Person #
##########


class PersonCreateView(LoginRequiredMixin, CreateView):
    model = Person
    form_class = PersonForm
    template_name = "read/person_create.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("read:person_detail", kwargs={"pk": self.object.pk})


class PersonDetailView(DetailView):
    model = Person
    template_name = "read/person_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["books"] = self.object.books.all().order_by("publication_date")
        context["editions_as_author"] = Edition.objects.filter(
            editionrole__role__name="Author", editionrole__person=self.object
        )
        context["editions_as_translator"] = Edition.objects.filter(
            editionrole__role__name="Translator", editionrole__person=self.object
        )
        return context


class PersonUpdateView(LoginRequiredMixin, UpdateView):
    model = Person
    form_class = PersonForm
    template_name = "read/person_update.html"

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("read:person_detail", kwargs={"pk": self.object.pk})


class RoleCreateView(LoginRequiredMixin, CreateView):
    model = Role
    fields = ["name"]
    template_name = "read/role_create.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse_lazy("activity_feed:activity_feed")


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
## Book ##
##########


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
        else:
            data["bookroles"] = BookRoleFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        bookroles = context["bookroles"]
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if bookroles.is_valid():
                bookroles.instance = self.object
                bookroles.save()
            else:
                print(bookroles.errors)  # print out formset errors
        return super().form_valid(form)


class BookUpdateView(LoginRequiredMixin, UpdateView):
    model = Book
    form_class = BookForm
    template_name = "read/book_update.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["bookroles"] = BookRoleFormSet(self.request.POST, instance=self.object)
        else:
            data["bookroles"] = BookRoleFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        bookroles = context["bookroles"]
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if bookroles.is_valid():
                bookroles.instance = self.object
                bookroles.save()
            else:
                print(bookroles.errors)  # print out formset errors
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("read:book_detail", kwargs={"pk": self.object.pk})


class BookDetailView(DetailView):
    model = Book
    template_name = "read/book_detail.html"


###########
# Edition #
###########


class EditionCreateView(LoginRequiredMixin, CreateView):
    model = Edition
    form_class = EditionForm
    template_name = "read/edition_create.html"

    def get_success_url(self):
        return reverse_lazy("read:edition_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["editionroles"] = EditionRoleFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["editionroles"] = EditionRoleFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        editionroles = context["editionroles"]
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if editionroles.is_valid():
                editionroles.instance = self.object
                editionroles.save()
        return super().form_valid(form)


class EditionDetailView(DetailView):
    model = Edition
    template_name = "read/edition_detail.html"


class EditionUpdateView(UpdateView):
    model = Edition
    form_class = EditionForm
    template_name = "read/edition_update.html"

    def get_success_url(self):
        return reverse_lazy("read:edition_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["editionroles"] = EditionRoleFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["editionroles"] = EditionRoleFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        editionroles = context["editionroles"]
        with transaction.atomic():
            form.instance.updated_by = self.request.user
            if self.request.method == "POST":
                form = EditionForm(
                    self.request.POST, self.request.FILES, instance=self.object
                )
                if form.is_valid():
                    self.object = form.save()
                    if editionroles.is_valid():
                        editionroles.instance = self.object
                        editionroles.save()
        return super().form_valid(form)


class BookAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Book.objects.none()

        qs = Book.objects.all()

        if self.q:
            qs = qs.filter(title__istartswith=self.q)

        return qs

    def get_result_label(self, item):
        # Get the first person with a role of 'Author' for the book
        author_role = Role.objects.filter(
            name="Author"
        ).first()  # Adjust 'Author' to match your data
        book_role = item.bookrole_set.filter(role=author_role).first()
        author_name = (
            book_role.person.name if book_role and book_role.person else "Unknown"
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


class PersonAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Person.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs

    def get_result_label(self, item):
        # Get the birth and death years
        birth_year = item.birth_date[:4] if item.birth_date else "Unk."
        death_year = item.death_date[:4] if item.death_date else "Pres."

        # Format the label
        label = format_html("{} ({} - {})", item.name, birth_year, death_year)

        return label


class RoleAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Role.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs
