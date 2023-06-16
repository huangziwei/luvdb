from dal import autocomplete
from django.db import transaction
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView

from .forms import BookForm, BookRoleFormSet, EditionForm, EditionRoleFormSet
from .models import Book, Edition, Person, Publisher, Role

##########
# Person #
##########


class PersonCreateView(CreateView):
    model = Person
    fields = ["name", "bio", "birth_date", "death_date"]
    template_name = "read/person_create.html"

    def get_success_url(self):
        return reverse_lazy("read:person_detail", kwargs={"pk": self.object.pk})


class PersonDetailView(DetailView):
    model = Person
    template_name = "read/person_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["editions_as_author"] = Edition.objects.filter(
            editionrole__role__name="Author", editionrole__person=self.object
        )
        context["editions_as_translator"] = Edition.objects.filter(
            editionrole__role__name="Translator", editionrole__person=self.object
        )
        return context


#############
# Publisher #
#############


class PublisherCreateView(CreateView):
    model = Publisher
    fields = ["name", "history", "location", "website", "founded_date", "closed_date"]
    template_name = "read/publisher_create.html"

    def get_success_url(self):
        return reverse_lazy("read:publisher_detail", kwargs={"pk": self.object.pk})


class PublisherDetailView(DetailView):
    model = Publisher
    template_name = "read/publisher_detail.html"


##########
## Book ##
##########


class BookCreateView(CreateView):
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
        return super().form_valid(form)


class BookDetailView(DetailView):
    model = Book
    template_name = "read/book_detail.html"


###########
# Edition #
###########


class EditionCreateView(CreateView):
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


class RoleAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Role.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs
