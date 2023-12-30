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
        }
        labels = {
            "historical": "Is this a historical location?",
            "historical_period": "Historical Period",
        }
