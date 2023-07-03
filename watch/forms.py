import re

from crispy_forms.bootstrap import Field
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Fieldset, Layout, Row, Submit
from dal import autocomplete
from django import forms
from django.conf import settings
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from .models import Movie, MovieCast, MovieRole, Series, SeriesRole


class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        exclude = ["created_by", "updated_by", "persons", "casts"]
        fields = "__all__"
        widgets = {
            "studios": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("watch:studio-autocomplete")
            ),
        }

    def __init__(self, *args, **kwargs):
        super(MovieForm, self).__init__(*args, **kwargs)
        self.fields["studios"].required = False


class MovieRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta:
        model = MovieRole
        fields = ("person", "role", "domain", "alt_name")


MovieRoleFormSet = inlineformset_factory(
    Movie,
    MovieRole,
    form=MovieRoleForm,
    extra=15,
    can_delete=True,
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:person-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:person_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
)


class MovieCastForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta:
        model = MovieCast
        fields = ("person", "role", "domain", "character_name")


MovieCastFormSet = inlineformset_factory(
    Movie,
    MovieCast,
    form=MovieCastForm,
    extra=15,
    can_delete=True,
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:person-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:person_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
)


class SeriesForm(forms.ModelForm):
    class Meta:
        model = Series
        exclude = ["created_by", "updated_by", "persons"]
        fields = "__all__"
        widgets = {
            "studios": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("watch:studio-autocomplete")
            ),
        }

    def __init__(self, *args, **kwargs):
        super(SeriesForm, self).__init__(*args, **kwargs)
        self.fields["studios"].required = False


class SeriesRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta:
        model = SeriesRole
        fields = ("person", "role", "domain", "alt_name")


SeriesRoleFormSet = inlineformset_factory(
    Series,
    SeriesRole,
    form=SeriesRoleForm,
    extra=15,
    can_delete=True,
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:person-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:person_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
)
