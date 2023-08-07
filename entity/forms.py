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
            "romanized_name",
            "birth_date",
            "birth_place",
            "death_date",
            "death_place",
            "wikipedia",
            "website",
        ]
        help_texts = {
            "name": "Enter the person's most-used name in their original language. ",
            "other_names": "Enter any other names the person is known by, separated by commas.",
            "romanized_name": "Enter the English or romanized version of the person's name.",
            "birth_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
            "birth_place": "Enter the place of birth in its original language.",
            "wikipedia": "Enter the person's Wikipedia URL.",
            "website": "Enter the person's website URL.",
        }
        widgets = {
            "other_names": forms.TextInput(),  # Use TextInput to make it a single line input
        }
