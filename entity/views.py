from dal import autocomplete
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView

# from listen.models import Release, Track
from read.models import Book, BookRole

from .forms import PersonForm
from .models import Person, Role


# Create your views here.
class PersonCreateView(LoginRequiredMixin, CreateView):
    model = Person
    form_class = PersonForm
    template_name = "entity/person_create.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("entity:person_detail", kwargs={"pk": self.object.pk})


class PersonDetailView(DetailView):
    model = Person
    template_name = "entity/person_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["works"] = self.object.works.all().order_by("publication_date")
        context["books_as_author"] = Book.objects.filter(
            bookrole__role__name="Author", bookrole__person=self.object
        ).order_by("publication_date")
        context["books_as_translator"] = Book.objects.filter(
            bookrole__role__name="Translator", bookrole__person=self.object
        ).order_by("publication_date")
        context["books_as_editor"] = Book.objects.filter(
            bookrole__role__name="Editor", bookrole__person=self.object
        ).order_by("publication_date")

        context["books"] = Book.objects.filter(persons=self.object).order_by(
            "language", "publication_date"
        )

        person = self.object
        book_roles = BookRole.objects.filter(person=person)

        # group roles by the Role name for display
        roles = {}
        for role in book_roles:
            role_name = str(role.role)
            if role_name != "Author":
                if role_name not in roles:
                    roles[role_name] = []
                roles[role_name].append(
                    {
                        "title": role.book.title,
                        "publication_date": role.book.publication_date,
                        "url": reverse("read:book_detail", args=[role.book.pk]),
                    }
                )

        context["roles"] = roles
        return context


class PersonUpdateView(LoginRequiredMixin, UpdateView):
    model = Person
    form_class = PersonForm
    template_name = "entity/person_update.html"

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("entity:person_detail", kwargs={"pk": self.object.pk})


class RoleCreateView(LoginRequiredMixin, CreateView):
    model = Role
    fields = ["name", "domain"]
    template_name = "entity/role_create.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse_lazy("activity_feed:activity_feed")


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
        if not self.request.user.is_authenticated:
            return Role.objects.none()

        domain = self.forwarded.get("domain", None)
        qs = Role.objects.all()

        if domain:
            qs = qs.filter(domain=domain)

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs
