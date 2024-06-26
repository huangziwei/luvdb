import auto_prefetch
from dal import autocomplete
from django import forms
from django.urls import reverse_lazy

from .models import Location, VisitCheckIn


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
            "osm_id_type",
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
            "osm_id": "Enter the location's <a href='https://www.openstreetmap.org/'>OpenStreetMap</a> ID.",
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
            "osm_id_type": "Type",
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
        self.fields["level"].required = True


class VisitCheckInForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = VisitCheckIn
        fields = [
            "content_type",
            "object_id",
            "user",
            "status",
            "progress",
            "progress_type",
            "content",
            "comments_enabled",
            "share_to_feed",
            "visibility",
        ]
        widgets = {
            "content_type": forms.HiddenInput(),
            "object_id": forms.HiddenInput(),
            "user": forms.HiddenInput(),
            "content": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Check in...",
                    "id": "text-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super(VisitCheckInForm, self).__init__(*args, **kwargs)
        self.fields["content"].label = ""
        self.fields["content"].required = False
        self.fields["comments_enabled"].label = "Enable replies"
