import auto_prefetch
from dal import autocomplete
from django import forms
from django.urls import reverse_lazy

from .models import Location


class LocationForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = Location
        fields = [
            "name",
            "other_names",
            "level",
            "parent",
            "historical",
            "historical_period",
            "current_identity",
            "address",
            "wikipedia",
            "website",
            "notes",
        ]
        help_texts = {
            "name": "Enter the name of the location in English.",
            "other_names": "Enter any other names the location is known by, separated by slashes (`/`). E.g. name in original language.",
            "level": "Select the geographical / administrative level of the location.",
            "parent": "Select the parent location of the location. <a href='/visit/location/create/'>Add a new location</a>.",
            "historical": "Check if the location is historical.",
            "historical_period": "Enter the historical period of the location.",
            "current_identity": "Select the current identity of the location. <a href='/visit/location/create/'>Add a new location</a>. Only required if the location is historical.",
            "address": "Enter the address of the location if it's a point of interest.",
            "wikipedia": "Enter the location's Wikipedia URL.",
            "website": "Enter the location's official website URL.",
            "notes": "Enter any additional information about the location.",
        }
        widgets = {
            "other_names": forms.TextInput(),
            "address": forms.TextInput(),
            "parent": autocomplete.ModelSelect2(
                url=reverse_lazy("visit:location-autocomplete"),
            ),
            "current_identity": autocomplete.ModelSelect2(
                url=reverse_lazy("visit:location-autocomplete"),
            ),
        }
        labels = {
            "historical": "Is this a historical location?",
            "historical_period": "Historical Period",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        custom_level_labels = {
            Location.CONTINENT: "Continent",
            Location.POLITY: "Polity",
            Location.REGION: "Region / State / Province / Canton / Prefecture",
            Location.CITY: "City / Municipality / County",
            Location.TOWN: "Town / Township",
            Location.VILLAGE: "Village / Hamlet",
            Location.DISTRICT: "District / Borough / Ward / Neighborhood",
            Location.POI: "Point of Interest",
            "": "Select Level",
        }
        self.fields["level"].choices = [
            (key, custom_level_labels[key]) for key, _ in self.fields["level"].choices
        ]
