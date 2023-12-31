import re
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
        if self.object.current_identity:
            context["current_identity_parents"] = self.get_parent_locations(
                self.object.current_identity
            )
        # Group children by their levels
        children_grouped_by_level_current = defaultdict(list)
        children_grouped_by_level_historical = defaultdict(list)
        for child in self.object.children.all().order_by("name"):
            level = self.get_level_label(child.level)
            if child.historical:
                children_grouped_by_level_historical[level].append(child)
            else:
                children_grouped_by_level_current[level].append(child)

        context["children_grouped_by_level_current"] = dict(
            children_grouped_by_level_current
        )
        context["children_grouped_by_level_historical"] = dict(
            children_grouped_by_level_historical
        )

        regex_pattern = r"(?:^|,)" + re.escape(str(self.object.id)) + r"(?:,|$)"
        context["creators_born_here"] = Creator.objects.filter(
            birth_location_hierarchy__regex=regex_pattern
        ).order_by("birth_date")
        context["creators_died_here"] = Creator.objects.filter(
            death_location_hierarchy__regex=regex_pattern
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

    def get_level_label(self, level):
        if level == Location.CONTINENT:
            return "Continent"
        elif level == Location.POLITY:
            return "Polities / Sovereign Entities"
        elif level == Location.REGION:
            return "Regions / States / Provinces / Cantons / Prefectures"
        elif level == Location.CITY:
            return "Cities / Municipalities / Counties"
        elif level == Location.TOWN:
            return "Towns / Townships"
        elif level == Location.VILLAGE:
            return "Villages / Hamlets"
        elif level == Location.DISTRICT:
            return "Districts / Boroughs / Wards / Neighborhoods"
        elif level == Location.POI:
            return "Points of Interest"


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
    template_name = "location_list.html"
    context_object_name = "locations"

    def get_queryset(self):
        # Retrieve only top-level locations (continents)
        return Location.objects.filter(level=Location.CONTINENT)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nested_locations"] = self._get_child_locations(
            None
        )  # Start with no parent
        return context

    def _get_child_locations(self, parent_location, depth=0):
        locations = Location.objects.filter(parent=parent_location).order_by("name")
        location_dict = {
            location: {
                "children": self._get_child_locations(location, depth + 1),
                "depth": depth,
                "historical": location.historical,
            }
            for location in locations
        }
        return location_dict


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
