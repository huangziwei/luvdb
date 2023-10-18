from django import forms

from .models import Person


##########
# Person #
##########
class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = [
            "name",
            "other_names",
            "creator_type",
            "birth_date",
            "birth_place",
            "death_date",
            "death_place",
            "wikipedia",
            "website",
            "notes",
        ]
        help_texts = {
            "name": "Enter the person's or the group's most-used name in their original language. ",
            "other_names": "Enter any other names the person or the group is known by, separated by slashes (`/`).",
            "creator_type": "Select whether the entity is a person or a group.",
            "birth_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
            "birth_place": "Enter the place of birth or formation in its original language.",
            "death_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
            "death_place": "Enter the place of death or dissolution in its original language.",
            "wikipedia": "Enter the person's or the group's Wikipedia URL.",
            "website": "Enter the person's or the group's website URL.",
            "notes": "Enter any additional information about the person or the group.",
        }
        widgets = {
            "other_names": forms.TextInput(),  # Use TextInput to make it a single line input
        }
        labels = {
            "birth_date": "Date of Birth / Formation",
            "birth_place": "Place of Birth / Formation",
            "death_date": "Date of Death / Dissolution",
            "death_place": "Place of Death / Dissolution",
        }
