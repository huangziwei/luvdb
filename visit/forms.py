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
            "level_name",
            "parent",
            "historical",
            "historical_period",
            "current_identity",
            "address",
            "wikipedia",
            "website",
            "osm_id",
            "notes",
        ]
        help_texts = {
            "name": "Enter the name of the location in English.",
            "other_names": "Enter any other names the location is known by, separated by slashes (`/`). E.g. name in original language.",
            "level": "Select the geographical/administrative level of the location. The labels are for suggestions only; please adapt to the actual situation.",
            "level_name": "Enter a custom label for the level. If left blank, the default label will be used.",
            "parent": "Select the parent location of the location. <a href='/visit/location/create/'>Add a new location</a>.",
            "historical": "Check if the location no longer exists or exists under another name.",
            "historical_period": "Enter the historical period of the location.",
            "current_identity": "Select the current identity of the location. <a href='/visit/location/create/'>Add a new location</a>. Only required if the location is historical.",
            "address": "Enter the address of the location if it's a point of interest.",
            "wikipedia": "Enter the location's Wikipedia URL.",
            "website": "Enter the location's official website URL.",
            "osm_id": "Enter the location's OpenStreetMap ID.",
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
            "historical_period": "Historical period",
            "osm_id": "OpenStreetMap ID",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        custom_level_labels = {
            Location.LEVEL0: "Level 0: Continent",
            Location.LEVEL1: "Level 1: Polity, Sovereign State, etc.",
            Location.LEVEL2: "Level 2: State, Province, Canton, Prefecture, Region, etc.",
            Location.LEVEL3: "Level 3: County, Municipality, Prefecture-level City, etc.",
            Location.LEVEL4: "Level 4: City, Town, Township, Village, Hamlet, etc.",
            Location.LEVEL5: "Level 5: District, Ward, Borough, Neighborhood etc.",
            Location.LEVEL6: "Level 6: Point of Interest",
            Location.LEVEL7: "Level 7: Others",
            "": "Select Level",
        }
        self.fields["level"].choices = [
            (key, custom_level_labels[key]) for key, _ in self.fields["level"].choices
        ]
