import auto_prefetch
from dal import autocomplete
from django import forms
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from .models import (
    Company,
    CompanyParent,
    CompanyPastName,
    CoverAlbum,
    CoverImage,
    Creator,
    MemberOf,
)


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
            "active_years",
            "origin_location",
            "wikipedia",
            "website",
            "notes",
        ]
        help_texts = {
            "name": "Enter the person's or the group's name in the language they are most widely recognized.  ",
            "other_names": "Enter any other names the person or the group is known by, separated by slashes (`/`).",
            "creator_type": "Select whether the entity is a person or a group.",
            "birth_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
            "birth_location": "Enter the person's location of birth. <a href='/visit/location/create/?next=/entity/creator/create/'>Add a new location</a>.",
            "death_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
            "death_location": "Enter the person's location of death. <a href='/visit/location/create/?next=/entity/creator/create/'>Add a new location</a>.",
            "active_years": "E.g. `YYYY-YYYY, YYYY, YYYY-`,",
            "origin_location": "Enter the group's location of origin. <a href='/visit/location/create/?next=/entity/creator/create/'>Add a new location</a>.",
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
            "origin_location": autocomplete.ModelSelect2(
                url=reverse_lazy("visit:location-autocomplete"),
            ),
        }
        labels = {
            "creator_type": "Type",
            "birth_date": "Date of Birth",
            "birth_location": "Place of Birth",
            "death_date": "Date of Death",
            "death_location": "Place of Death",
            "active_years": "Years Active",
            "origin_location": "Place of Origin",
        }


class MemberOfForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = MemberOf
        fields = ("group", "start_date", "end_date")

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        group = cleaned_data.get("group")
        if creator == group:
            raise forms.ValidationError("Creator and group cannot be the same")
        return cleaned_data

    def fsave(self, commit=True):
        instance = super().save(commit=False)
        if instance.group is None:
            if commit and instance.pk:
                instance.delete()
            return None
        if commit:
            instance.save()
        return instance


MemberOfFormSet = forms.inlineformset_factory(
    Creator,
    MemberOf,
    fk_name="creator",
    form=MemberOfForm,
    fields=("group", "notes", "start_date", "end_date"),
    extra=1,
    can_delete=True,
    widgets={
        "group": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:group-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
    },
)


class CompanyForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = Company
        fields = [
            "name",
            "other_names",
            "location",
            "founded_date",
            "defunct_date",
            "wikipedia",
            "website",
            "notes",
        ]
        help_texts = {
            "name": "Enter name of the company",
            "other_names": "Enter any other names of the company is known by, separated by slashes (`/`).",
            "location": "Enter the location of the company. <a href='/visit/location/create/?next=/entity/creator/create/'>Add a new location</a>.",
            "founded_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
            "defunct_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
            "wikipedia": "Enter the company's Wikipedia URL.",
            "website": "Enter the company's website URL.",
            "notes": "Enter any additional information about the person or the group.",
        }
        widgets = {
            "other_names": forms.TextInput(),  # Use TextInput to make it a single line input
            "location": autocomplete.ModelSelect2(
                url=reverse_lazy("visit:location-autocomplete"),
            ),
        }
        labels = {
            "location": "Location",
        }


class CompanyParentForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = CompanyParent
        fields = ("child", "parent", "start_date", "end_date")

    def clean(self):
        cleaned_data = super().clean()
        child = cleaned_data.get("child")
        parent = cleaned_data.get("parent")
        if child == parent:
            raise forms.ValidationError("Child and parent cannot be the same")
        return cleaned_data

    def fsave(self, commit=True):
        instance = super().save(commit=False)
        if instance.parent is None:
            if commit and instance.pk:
                instance.delete()
            return None
        if commit:
            instance.save()
        return instance


CompanyParentFormSet = forms.inlineformset_factory(
    Company,
    CompanyParent,
    fk_name="child",
    form=CompanyParentForm,
    fields=("parent", "alt_name", "start_date", "end_date"),
    extra=1,
    can_delete=True,
    widgets={
        "parent": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:company-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
    },
)


class CompanyPastNameForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = CompanyPastName
        fields = ("name", "start_date", "end_date")

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.name is None:
            if commit and instance.pk:
                instance.delete()
            return None
        if commit:
            instance.save()
        return instance


CompanyPastNameFormSet = forms.inlineformset_factory(
    Company,
    CompanyPastName,
    form=CompanyPastNameForm,
    fields=("name", "start_date", "end_date"),
    extra=1,
    can_delete=True,
)


###############
# Cover Album #
###############

class CoverImageForm(forms.ModelForm):
    class Meta:
        model = CoverImage
        fields = ["image", "is_primary"]


CoverImageFormSet = inlineformset_factory(
    CoverAlbum, CoverImage, form=CoverImageForm, extra=1, can_delete=True
)