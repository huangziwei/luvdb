from collections import defaultdict

from dal import autocomplete
from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django_ratelimit.decorators import ratelimit

from entity.models import Company, Creator
from entity.views import HistoryViewMixin, get_contributors

from .forms import LocationForm
from .models import Location

# Create your views here.


class LocationCreateView(LoginRequiredMixin, CreateView):
    model = Location
    form_class = LocationForm
    template_name = "visit/location_create.html"

    def get_success_url(self):
        return reverse_lazy("visit:location_detail", kwargs={"pk": self.object.pk})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["other_names"].widget = forms.TextInput()
        form.fields["address"].widget = forms.TextInput()
        return form

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class LocationDetailView(DetailView):
    model = Location
    template_name = "visit/location_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parent_locations"] = self.get_parent_locations(self.object)
        # Group children by their levels
        children_grouped_by_level = defaultdict(list)
        for child in self.object.children.all().order_by("name"):
            children_grouped_by_level[child.level].append(child)

        context["children_grouped_by_level"] = dict(children_grouped_by_level)
        context["creators_born_here"] = Creator.objects.filter(
            birth_location=self.object
        ).order_by("birth_date")
        context["creators_died_here"] = Creator.objects.filter(
            death_location=self.object
        ).order_by("death_date")
        context["companies_here"] = Company.objects.filter(
            location_new=self.object
        ).order_by("name")

        context["contributors"] = get_contributors(self.object)

        return context

    def get_parent_locations(self, location):
        parents = []
        current = location.parent
        while current is not None:
            parents.insert(0, current)
            current = current.parent
        return parents


class LocationUpdateView(UpdateView):
    model = Location
    form_class = LocationForm
    template_name = "visit/location_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("visit:location_detail", kwargs={"pk": self.object.pk})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["other_names"].widget = forms.TextInput()
        form.fields["address"].widget = forms.TextInput()
        return form

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class LocationListView(ListView):
    model = Location
    template_name = "visit/location_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Group locations by level and then by parent
        locations_grouped = defaultdict(lambda: defaultdict(list))
        for location in Location.objects.all():
            locations_grouped[location.level][location.parent_id].append(location)

        context["locations_grouped"] = dict(locations_grouped)

        return context


class LocationAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Location.objects.all()

        if self.q:
            qs = qs.filter(
                Q(name__icontains=self.q) | Q(other_names__icontains=self.q)
            ).distinct()

            return qs

        return Location.objects.none()


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class LocationHistoryView(HistoryViewMixin, DetailView):
    model = Location
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_object()
        context["history_data"] = self.get_history_data(company)
        return context
