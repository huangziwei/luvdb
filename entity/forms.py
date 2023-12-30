import auto_prefetch
from dal import autocomplete
from django import forms
from django.urls import reverse_lazy

from .models import Company, Creator


class CreatorForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = Creator
        fields = [
            "name",
            "other_names",
            "creator_type",
            "birth_date",
            "birth_location",
            "death_date",
            "death_location",
            "wikipedia",
            "website",
            "notes",
        ]
        help_texts = {
            "name": "Enter the person's or the group's most-used name in their original language. ",
            "other_names": "Enter any other names the person or the group is known by, separated by slashes (`/`).",
            "creator_type": "Select whether the entity is a person or a group.",
            "birth_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
            "birth_location": "Enter the location of birth or formation. <a href='/visit/location/create/?next=/entity/creator/create/'>Add a new location</a>.",
            "death_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
            "death_location": "Enter the place of death or dissolution. <a href='/visit/location/create/?next=/entity/creator/create/'>Add a new location</a>.",
            "wikipedia": "Enter the person's or the group's Wikipedia URL.",
            "website": "Enter the person's or the group's website URL.",
            "notes": "Enter any additional information about the person or the group.",
        }
        widgets = {
            "other_names": forms.TextInput(),  # Use TextInput to make it a single line input
            "birth_location": autocomplete.ModelSelect2(
                url=reverse_lazy("visit:location-autocomplete"),
            ),
            "death_location": autocomplete.ModelSelect2(
                url=reverse_lazy("visit:location-autocomplete"),
            ),
        }
        labels = {
            "creator_type": "Type",
            "birth_date": "Date of Birth / Formation",
            "birth_location": "Place of Birth / Formation",
            "death_date": "Date of Death / Dissolution",
            "death_location": "Place of Death / Dissolution",
        }


class CompanyForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = Company
        fields = [
            "name",
            "other_names",
            "location_new",
            "founded_date",
            "defunct_date",
            "wikipedia",
            "website",
            "notes",
        ]
        help_texts = {
            "name": "Enter name of the company",
            "other_names": "Enter any other names of the company is known by, separated by slashes (`/`).",
            "location_new": "Enter the location of the company. <a href='/visit/location/create/?next=/entity/creator/create/'>Add a new location</a>.",
            "founded_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
            "defunct_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
            "wikipedia": "Enter the company's Wikipedia URL.",
            "website": "Enter the company's website URL.",
            "notes": "Enter any additional information about the person or the group.",
        }
        widgets = {
            "other_names": forms.TextInput(),  # Use TextInput to make it a single line input
            "location_new": autocomplete.ModelSelect2(
                url=reverse_lazy("visit:location-autocomplete"),
            ),
        }
        labels = {
            "location_new": "Location",
        }
