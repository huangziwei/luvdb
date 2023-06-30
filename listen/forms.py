import re

from dal import autocomplete
from django import forms
from django.conf import settings
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from .models import (
    ListenCheckIn,
    Release,
    ReleaseRole,
    ReleaseTrack,
    Track,
    TrackRole,
    Work,
    WorkRole,
)


########
# Work #
########
class WorkForm(forms.ModelForm):
    class Meta:
        model = Work
        exclude = ["created_by", "updated_by", "persons"]
        fields = "__all__"
        help_texts = {
            "title": "Enter the work's title in its original language. ",
            "release_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["release_date"].label = "First Release Date"
        self.fields["genre"].label = "Genre(s)"
        self.fields["genre"].help_text = "e.g. pop, rock, jazz, etc."


class WorkRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="listen", widget=forms.HiddenInput())

    class Meta:
        model = WorkRole
        fields = ["person", "role", "domain"]


WorkRoleFormSet = inlineformset_factory(
    Work,
    WorkRole,
    form=WorkRoleForm,
    extra=15,
    can_delete=True,
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:person-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:person_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],  # forward the domain field to the RoleAutocomplete view
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
)


class TrackForm(forms.ModelForm):
    class Meta:
        model = Track
        exclude = ["created_by", "updated_by", "persons"]
        fields = "__all__"
        help_texts = {
            "title": "Enter the track's title. ",
            "release_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
        }
        widgets = {
            "work": autocomplete.ModelSelect2(
                url=reverse_lazy("listen:work-autocomplete")
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["release_date"].label = "Release Date"


class TrackRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="listen", widget=forms.HiddenInput())

    class Meta:
        model = TrackRole
        fields = ["person", "alt_name", "role", "domain"]


TrackRoleFormSet = inlineformset_factory(
    Track,
    TrackRole,
    form=TrackRoleForm,
    extra=15,
    can_delete=True,
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:person-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:person_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],  # forward the domain field to the RoleAutocomplete view
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
)


###########
# Release #
###########
class ReleaseForm(forms.ModelForm):
    class Meta:
        model = Release
        exclude = [
            "created_by",
            "updated_by",
            "works",
            "tracks",
            "persons",
        ]
        fields = "__all__"
        widgets = {
            "track": autocomplete.ModelSelect2(
                url=reverse_lazy("listen:track-autocomplete")
            ),
            "label": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("listen:label-autocomplete")
            ),
        }
        help_texts = {
            "release_format": "e.g. CD, digital, etc.",
        }

    def __init__(self, *args, **kwargs):
        super(ReleaseForm, self).__init__(*args, **kwargs)
        self.fields["cover_sens"].label = "Is the cover sensitive or explicit?"


class ReleaseRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="listen", widget=forms.HiddenInput())

    class Meta:
        model = ReleaseRole
        fields = ("person", "role", "domain", "alt_name")


ReleaseRoleFormSet = inlineformset_factory(
    Release,
    ReleaseRole,
    form=ReleaseRoleForm,
    extra=10,
    can_delete=True,
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:person-autocomplete"),
            attrs={
                "data-create-url": reverse_lazy("entity:person_create"),
                "data-placeholder": "Type to search",
            },
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],  # forward the domain field to the RoleAutocomplete view
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
)


class ReleaseTrackForm(forms.ModelForm):
    class Meta:
        model = ReleaseTrack
        fields = ["track", "order"]


ReleaseTrackFormSet = inlineformset_factory(
    Release,
    ReleaseTrack,
    form=ReleaseTrackForm,
    extra=100,
    can_delete=True,
    widgets={
        "track": autocomplete.ModelSelect2(
            url=reverse_lazy("listen:track-autocomplete"),
            attrs={
                "data-create-url": reverse_lazy("listen:track_create"),
                "data-placeholder": "Type to search",
            },
        ),
    },
)


class ListenCheckInForm(forms.ModelForm):
    class Meta:
        model = ListenCheckIn
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
        super(ListenCheckInForm, self).__init__(*args, **kwargs)
        self.fields["content"].label = ""
        self.fields["content"].required = False
