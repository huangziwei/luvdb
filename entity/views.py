from dal import autocomplete
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView

from listen.models import Release, Track
from listen.models import Work as MusicWork
from play.models import Game
from play.models import Work as GameWork
from read.models import Book, BookRole
from read.models import Instance as LitInstance
from read.models import Work as LitWork
from watch.models import Movie, Series

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
        person = self.object
        # read
        context["read_works"] = person.read_works.all().order_by("publication_date")

        as_translator = LitInstance.objects.filter(
            instancerole__role__name="Translator", instancerole__person=person
        ).order_by("publication_date")
        context["as_translator"] = as_translator

        # listen
        context["listen_works"] = person.listen_works.all().order_by("release_date")
        context["works_as_singer"] = MusicWork.objects.filter(
            workrole__role__name="Singer", workrole__person=person
        ).order_by("release_date")
        context["works_as_composer"] = MusicWork.objects.filter(
            workrole__role__name="Composer", workrole__person=person
        ).order_by("release_date")
        context["works_as_lyricist"] = MusicWork.objects.filter(
            workrole__role__name="Lyricist", workrole__person=person
        ).order_by("release_date")
        context["works_as_producer"] = MusicWork.objects.filter(
            workrole__role__name="Producer", workrole__person=person
        ).order_by("release_date")
        context["works_as_arranger"] = MusicWork.objects.filter(
            workrole__role__name="Arranger", workrole__person=person
        ).order_by("release_date")

        # watch
        ## as casts
        context["movies"] = (
            Movie.objects.filter(moviecasts__person=person)
            .distinct()
            .order_by("release_date")
        )
        context["series"] = (
            Series.objects.filter(episodes__episodecasts__person=person)
            .distinct()
            .order_by("release_date")
        )
        ## as staff
        context["movies_as_director"] = (
            Movie.objects.filter(
                movieroles__person=person, movieroles__role__name="Director"
            )
            .distinct()
            .order_by("release_date")
        )
        context["series_as_director"] = (
            Series.objects.filter(
                seriesroles__person=person, seriesroles__role__name="Director"
            )
            .distinct()
            .order_by("release_date")
        )

        context["movies_as_writer"] = (
            Movie.objects.filter(
                movieroles__person=person, movieroles__role__name="Writer"
            )
            .distinct()
            .order_by("release_date")
        )
        context["series_as_writer"] = (
            Series.objects.filter(
                seriesroles__person=person, seriesroles__role__name="Writer"
            )
            .distinct()
            .order_by("release_date")
        )

        # play
        context["gameworks"] = (
            GameWork.objects.filter(
                workrole__role__name="Writer", workrole__person=person
            )
            .distinct()
            .order_by("first_release_date")
        )

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


class RoleUpdateView(LoginRequiredMixin, UpdateView):
    model = Role
    fields = ["name", "domain"]
    template_name = "entity/role_update.html"

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse_lazy("activity_feed:activity_feed")


class RoleDetailView(LoginRequiredMixin, DetailView):
    model = Role
    template_name = "entity/role_detail.html"


class PersonAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Person.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

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

        return qs[:5]
