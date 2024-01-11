import re

import auto_prefetch
from dal import autocomplete
from django import forms
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from entity.models import Role

from .models import (
    Audiobook,
    AudiobookInstance,
    AudiobookRole,
    ListenCheckIn,
    Release,
    ReleaseGroup,
    ReleaseInGroup,
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
    class Meta(auto_prefetch.Model.Meta):
        model = Work
        exclude = ["created_by", "updated_by", "creators", "locked"]
        fields = "__all__"
        help_texts = {
            "title": "Enter the work's title in its original language. ",
            "release_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
            "recorded_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`. ",
        }

        widgets = {
            "genres": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("listen:genre-autocomplete")
            ),
            "other_titles": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["release_date"].label = "First Release Date"
        self.fields["recorded_date"].label = "First Recorded Date"
        self.fields[
            "other_titles"
        ].help_text = (
            "e.g. translated titles in different languages, separated by slashes (`/`)."
        )


class WorkRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="listen", widget=forms.HiddenInput())

    class Meta(auto_prefetch.Model.Meta):
        model = WorkRole
        fields = ["creator", "alt_name", "role", "domain"]

    def __init__(self, *args, **kwargs):
        super(WorkRoleForm, self).__init__(*args, **kwargs)
        # Set default role to "Performer"
        try:
            default_role = Role.objects.get(name="Singer")
            self.fields["role"].initial = default_role
        except ObjectDoesNotExist:
            # If "Performer" role does not exist, the initial will be None as before
            pass

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the person field is filled but the role field is not
        if creator and not role:
            raise ValidationError("Role is required when Creator is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.creator is None:  # if the person field is empty
            if commit and instance.pk:
                instance.delete()
            return None
        if commit:
            instance.save()
        return instance


WorkRoleFormSet = inlineformset_factory(
    Work,
    WorkRole,
    form=WorkRoleForm,
    extra=1,
    can_delete=True,
    widgets={
        "creator": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],  # forward the domain field to the RoleAutocomplete view
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
    help_texts={
        "creator": "<a href='/entity/creator/create/'>Add a new creator</a>.",
        "role": "<a href='/entity/role/create/'>Add a new role</a>.",
    },
)


class TrackForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = Track
        exclude = ["created_by", "updated_by", "creators", "locked"]
        fields = "__all__"
        help_texts = {
            "title": "Enter the track's title. ",
            "release_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
            "recorded_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`. ",
            "length": "Enter the track's length, e.g. 3:45",
        }
        widgets = {
            "work": autocomplete.ModelSelect2(
                url=reverse_lazy("listen:work-autocomplete")
            ),
            "genres": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("listen:genre-autocomplete")
            ),
            "other_titles": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["release_date"].label = "Release Date"
        self.fields[
            "other_titles"
        ].help_text = (
            "e.g. translated titles in different languages, separated by slashes (`/`)."
        )


class TrackRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="listen", widget=forms.HiddenInput())

    class Meta(auto_prefetch.Model.Meta):
        model = TrackRole
        fields = ["creator", "alt_name", "role", "domain"]

    def __init__(self, *args, **kwargs):
        super(TrackRoleForm, self).__init__(*args, **kwargs)
        # Set default role to "Performer"
        try:
            default_role = Role.objects.get(name="Singer")
            self.fields["role"].initial = default_role
        except ObjectDoesNotExist:
            # If "Performer" role does not exist, the initial will be None as before
            pass

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the person field is filled but the role field is not
        if creator and not role:
            raise ValidationError("Role is required when Creator is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.creator is None:  # if the person field is empty
            if commit and instance.pk:
                instance.delete()
            return None
        if commit:
            instance.save()
        return instance


TrackRoleFormSet = inlineformset_factory(
    Track,
    TrackRole,
    form=TrackRoleForm,
    extra=1,
    can_delete=True,
    widgets={
        "creator": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],  # forward the domain field to the RoleAutocomplete view
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
    help_texts={
        "creator": "<a href='/entity/creator/create/'>Add a new creator</a>.",
        "role": "<a href='/entity/role/create/'>Add a new role</a>.",
    },
)


###########
# Release #
###########
class ReleaseForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = Release
        exclude = ["created_by", "updated_by", "works", "tracks", "creators", "locked"]
        fields = "__all__"
        widgets = {
            "track": autocomplete.ModelSelect2(
                url=reverse_lazy("listen:track-autocomplete")
            ),
            "label": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("entity:company-autocomplete")
            ),
            "genres": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("listen:genre-autocomplete")
            ),
            "other_titles": forms.TextInput(),
        }
        help_texts = {
            "release_format": "For the medium of the release, e.g. Vinyl, CD, Digital, etc.",
            "release_type": " For the length of the release, e.g. Single, EP, LP, etc.",
            "recording_type": "e.g. Live, Studio, etc.",
            "other_titles": "e.g. translated titles in different languages, separated by slashes (`/`).",
            "apple_music_url": "add `geo` in the beginning of the URL to redirect to the user's country, e.g. `https://geo.music.apple.com/us/album/...`",
        }

    def __init__(self, *args, **kwargs):
        super(ReleaseForm, self).__init__(*args, **kwargs)
        self.fields["cover_sens"].label = "Is the cover sensitive or explicit?"
        self.fields["label"].required = False


class ReleaseRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="listen", widget=forms.HiddenInput())

    class Meta(auto_prefetch.Model.Meta):
        model = ReleaseRole
        fields = ("creator", "role", "domain", "alt_name")

    def __init__(self, *args, **kwargs):
        super(ReleaseRoleForm, self).__init__(*args, **kwargs)
        # Set default role to "Performer"
        try:
            default_role = Role.objects.get(name="Performer")
            self.fields["role"].initial = default_role
        except ObjectDoesNotExist:
            # If "Performer" role does not exist, the initial will be None as before
            pass

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the person field is filled but the role field is not
        if creator and not role:
            raise ValidationError("Role is required when Creator is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.creator is None:  # if the person field is empty
            if commit and instance.pk:
                instance.delete()
            return None
        if commit:
            instance.save()
        return instance


ReleaseRoleFormSet = inlineformset_factory(
    Release,
    ReleaseRole,
    form=ReleaseRoleForm,
    extra=1,
    can_delete=True,
    widgets={
        "creator": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={
                "data-create-url": reverse_lazy("entity:creator_create"),
                "data-placeholder": "Type to search",
            },
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],  # forward the domain field to the RoleAutocomplete view
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
    help_texts={
        "creator": "<a href='/entity/creator/create/'>Add a new creator</a>.",
        "role": "<a href='/entity/role/create/'>Add a new role</a>.",
    },
)


class ReleaseTrackForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = ReleaseTrack
        fields = ["track", "alt_title", "order", "disk"]

    def clean(self):
        cleaned_data = super().clean()
        instance = cleaned_data.get("track")
        if self.instance and not instance:  # if the instance field is empty
            self.instance.delete()  # delete the AudiobookInstance instance
        return cleaned_data


ReleaseTrackFormSet = inlineformset_factory(
    Release,
    ReleaseTrack,
    form=ReleaseTrackForm,
    extra=1,
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
    help_texts={
        "track": "<a href='/listen/track/create/'>Add a new track</a>.",
    },
)


class ListenCheckInForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
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


#################
# Release Group #
#################


class ReleaseGroupForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = ReleaseGroup
        fields = ["title"]


class ReleaseInGroupForm(forms.ModelForm):
    release_url = forms.URLField()

    class Meta(auto_prefetch.Model.Meta):
        model = ReleaseInGroup
        fields = ["release_url"]
        exclude = ["release_group"]

    def clean_release_url(self):
        release_url = self.cleaned_data.get("release_url")
        if not release_url:  # if the field is empty, just return it
            return release_url
        release_id = re.findall(r"release/(\d+)", release_url)
        if not release_id:
            raise forms.ValidationError("Invalid Release URL")
        try:
            release = Release.objects.get(pk=release_id[0])
        except Release.DoesNotExist:
            raise forms.ValidationError("Release does not exist")
        self.instance.release = release  # save the release instance directly
        return release_url

    def clean(self):
        cleaned_data = super().clean()
        release_url = cleaned_data.get("release_url")
        if not release_url:  # if the release_url field is empty
            self.cleaned_data["DELETE"] = True  # mark the form for deletion
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super(ReleaseInGroupForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.release:
            self.fields[
                "release_url"
            ].initial = f"{settings.ROOT_URL}/listen/release/{self.instance.release.pk}"
        self.fields["release_url"].required = False
        self.fields["release_url"].label = "URL"


ReleaseInGroupFormSet = forms.inlineformset_factory(
    ReleaseGroup, ReleaseInGroup, form=ReleaseInGroupForm, extra=2, can_delete=True
)


#############
# Audiobook #
#############
class AudiobookForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = Audiobook
        exclude = [
            "created_by",
            "updated_by",
            "works",
            "instances",
            "creators",
            "locked",
        ]
        fields = "__all__"
        widgets = {
            "instance": autocomplete.ModelSelect2(
                url=reverse_lazy("read:instance-autocomplete")
            ),
            "publisher": autocomplete.ModelSelect2(
                url=reverse_lazy("entity:company-autocomplete")
            ),
            "language": autocomplete.ListSelect2(url="read:language-autocomplete"),
            "release_date": forms.TextInput(),
        }
        help_texts = {
            "format": "e.g. paperback, hardcover, ebook, etc.",
            "length": "e.g. 300 pages, 10:20:33, etc.",
            "release_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`. For books published before common era, use negative numbers, e.g. `-100`.",
        }

    def __init__(self, *args, **kwargs):
        super(AudiobookForm, self).__init__(*args, **kwargs)
        self.fields["cover_sens"].label = "Is the cover sensitive or explicit?"
        self.fields["publisher"].required = False


class AudiobookRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="read", widget=forms.HiddenInput())

    class Meta(auto_prefetch.Model.Meta):
        model = AudiobookRole
        fields = ("creator", "role", "domain", "alt_name")

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the person field is filled but the role field is not
        if creator and not role:
            raise ValidationError("Role is required when Creator is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.creator is None:  # if the person field is empty
            if commit and instance.pk:
                instance.delete()
            return None
        if commit:
            instance.save()
        return instance


AudiobookRoleFormSet = inlineformset_factory(
    Audiobook,
    AudiobookRole,
    form=AudiobookRoleForm,
    extra=1,
    can_delete=True,
    widgets={
        "creator": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={
                "data-create-url": reverse_lazy("entity:creator_create"),
                "data-placeholder": "Type to search",
            },
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],  # forward the domain field to the RoleAutocomplete view
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
    help_texts={
        "creator": "<a href='/entity/creator/create/'>Add a new creator</a>.",
        "role": "<a href='/entity/role/create/'>Add a new role</a>.",
    },
)


class AudiobookInstanceForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = AudiobookInstance
        fields = ["instance", "order"]

    def clean(self):
        cleaned_data = super().clean()
        instance = cleaned_data.get("instance")
        if self.instance and not instance:  # if the instance field is empty
            self.instance.delete()  # delete the AudiobookInstance instance
        return cleaned_data


AudiobookInstanceFormSet = inlineformset_factory(
    Audiobook,
    AudiobookInstance,
    form=AudiobookInstanceForm,
    extra=1,
    can_delete=True,
    widgets={
        "instance": autocomplete.ModelSelect2(
            url=reverse_lazy("read:instance-autocomplete"),
            attrs={
                "data-create-url": reverse_lazy("read:instance_create"),
                "data-placeholder": "Type to search",
            },
        ),
    },
    help_texts={
        "instance": "<a href='/read/instance/create/'>Add a new instance</a>.",
    },
)
