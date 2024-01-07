import re
from collections import defaultdict
from operator import attrgetter

from dal import autocomplete
from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django_ratelimit.decorators import ratelimit

from entity.models import Company, Creator
from entity.views import HistoryViewMixin, get_contributors
from play.models import Work as GameWork
from read.models import Work as Publicaiton
from watch.models import Episode, Movie, Series

from .forms import LocationForm
from .models import Location
from .utils import get_parent_locations

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
        context["parent_locations"] = get_parent_locations(self.object)
        if self.object.current_identity:
            context["current_identity_parents"] = get_parent_locations(
                self.object.current_identity
            )
        # Group children by their levels
        children_grouped_by_level_current = defaultdict(list)
        children_grouped_by_level_historical = defaultdict(list)
        for child in self.object.children.all().order_by("name"):
            level = child.level_name
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
        creators_born_here_persons = Creator.objects.filter(
            birth_location_hierarchy__regex=regex_pattern,
            creator_type="person",  # Adjust the filter based on your model
        ).order_by("birth_date")

        creators_born_here_groups = Creator.objects.filter(
            birth_location_hierarchy__regex=regex_pattern,
            creator_type="group",  # Adjust the filter based on your model
        ).order_by("birth_date")

        context["creators_born_here_persons"] = creators_born_here_persons
        context["creators_born_here_groups"] = creators_born_here_groups

        context["creators_died_here"] = Creator.objects.filter(
            death_location_hierarchy__regex=regex_pattern
        ).order_by("death_date")
        context["companies_here"] = Company.objects.filter(
            location_hierarchy__regex=regex_pattern
        ).order_by("name")

        context["contributors"] = get_contributors(self.object)

        context["movies_filmed_here"] = Movie.objects.filter(
            filming_locations_hierarchy__regex=regex_pattern
        ).order_by("title")
        context["movies_set_here"] = sorted(
            Movie.objects.filter(setting_locations_hierarchy__regex=regex_pattern),
            key=attrgetter("earliest_release_date"),
        )

        episodes_filmed_here = Episode.objects.filter(
            filming_locations_hierarchy__regex=regex_pattern
        )
        episodes_set_here = Episode.objects.filter(
            setting_locations_hierarchy__regex=regex_pattern
        )

        series_ids_filmed = episodes_filmed_here.values_list(
            "series", flat=True
        ).distinct()
        series_ids_set = episodes_set_here.values_list("series", flat=True).distinct()
        context["series_filmed_here"] = Series.objects.filter(
            id__in=series_ids_filmed
        ).order_by("title")
        context["series_set_here"] = Series.objects.filter(
            id__in=series_ids_set
        ).order_by("title")

        context["publications_set_here"] = Publicaiton.objects.filter(
            related_locations_hierarchy__regex=regex_pattern
        ).order_by("publication_date")

        context["games_set_here"] = GameWork.objects.filter(
            setting_locations_hierarchy__regex=regex_pattern
        ).order_by("first_release_date")

        return context

    def get_level_label(self, level):
        if level == Location.LEVEL0:
            return "Continent"
        elif level == Location.LEVEL1:
            return "Polities / Sovereign Entities"
        elif level == Location.LEVEL2:
            return "Regions / States / Provinces / Cantons / Prefectures"
        elif level == Location.LEVEL3:
            return "Cities / Municipalities / Counties"
        elif level == Location.LEVEL4:
            return "Towns / Townships"
        elif level == Location.LEVEL5:
            return "Villages / Hamlets"
        elif level == Location.LEVEL6:
            return "Districts / Boroughs / Wards / Neighborhoods"
        elif level == Location.LEVEL7:
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
        return (
            Location.objects.filter(level=Location.LEVEL0, historical=False)
            .prefetch_related("children")
            .order_by("name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nested_locations"] = self._get_child_locations_dict()
        return context

    def _get_child_locations_dict(self):
        locations = (
            Location.objects.filter(historical=False)
            .order_by("level", "name")
            .select_related("parent")
        )
        location_tree = defaultdict(dict)

        for loc in locations:
            location_tree[loc.parent_id][loc] = {
                "depth": int(loc.level[5:]),  # Adjust as needed
            }

        return self._build_location_hierarchy(location_tree)

    def _build_location_hierarchy(self, location_tree, parent_id=None):
        result = {}
        for loc, details in location_tree[parent_id].items():
            children = self._build_location_hierarchy(location_tree, parent_id=loc.id)
            result[loc] = {**details, "children": children}
        return result


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
