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
            "romanized_name",
            "birth_date",
            "birth_place",
            "death_date",
            "death_place",
            "wikipedia",
            "website",
        ]
        help_texts = {
            "name": "Enter the person's name in their original language. ",
            "romanized_name": "Enter the romanized version of the person's name.",
            "birth_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
            "birth_place": "Enter the place of birth in its original language.",
            "wikipedia": "Enter the person's Wikipedia URL.",
            "website": "Enter the person's website URL.",
        }
