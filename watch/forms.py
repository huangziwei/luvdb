import re

from crispy_forms.bootstrap import Field
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Fieldset, Layout, Row, Submit
from dal import autocomplete
from django import forms
from django.conf import settings
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from .models import (
    Episode,
    EpisodeCast,
    EpisodeRole,
    Movie,
    MovieCast,
    MovieRole,
    Series,
    SeriesRole,
    WatchCheckIn,
)


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


class EpisodeForm(forms.ModelForm):
    class Meta:
        model = Episode
        exclude = ["created_by", "updated_by", "persons", "casts"]
        fields = "__all__"


class EpisodeRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta:
        model = EpisodeRole
        fields = ("person", "role", "domain", "alt_name")


EpisodeRoleFormSet = inlineformset_factory(
    Episode,
    EpisodeRole,
    form=EpisodeRoleForm,
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


class EpisodeCastForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta:
        model = EpisodeCast
        fields = ("person", "role", "domain", "character_name")


EpisodeCastFormSet = inlineformset_factory(
    Episode,
    EpisodeCast,
    form=EpisodeCastForm,
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


class WatchCheckInForm(forms.ModelForm):
    class Meta:
        model = WatchCheckIn
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
        ]
        widgets = {
            "content_type": forms.HiddenInput(),
            "object_id": forms.HiddenInput(),
            "user": forms.HiddenInput(),  # user is now included
            "content": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Check in...",
                    "id": "text-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super(WatchCheckInForm, self).__init__(*args, **kwargs)
        self.fields["content"].label = ""
        self.fields["content"].required = False