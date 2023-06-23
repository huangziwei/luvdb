from crispy_forms.bootstrap import Field
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Fieldset, Layout, Row, Submit
from dal import autocomplete
from django import forms
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from .models import Game, GameCheckIn, GameRole


class GameForm(forms.ModelForm):
    class Meta:
        model = Game
        exclude = ["created_by", "updated_by", "persons"]
        fields = "__all__"
        widgets = {
            "developers": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("play:developer-autocomplete")
            ),
            "platforms": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("play:platform-autocomplete")
            ),
        }

    def __init__(self, *args, **kwargs):
        super(GameForm, self).__init__(*args, **kwargs)
        self.fields["developers"].required = False
        self.fields["platforms"].required = False


class GameRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="play", widget=forms.HiddenInput())

    class Meta:
        model = GameRole
        fields = ("person", "role", "domain", "alt_name")


GameRoleFormSet = inlineformset_factory(
    Game,
    GameRole,
    form=GameRoleForm,
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


class GameCheckInForm(forms.ModelForm):
    class Meta:
        model = GameCheckIn
        fields = [
            "game",
            "user",
            "status",
            "progress",
            "progress_type",
            "content",
            "comments_enabled",
            "share_to_feed",
        ]
        widgets = {
            "game": forms.HiddenInput(),
            "user": forms.HiddenInput(),  # author is now included
            "content": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Check in...",
                    "id": "text-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super(GameCheckInForm, self).__init__(*args, **kwargs)
        self.fields["content"].label = ""
        self.fields["content"].required = False
        self.fields["comments_enabled"].label = "Enable comments"
        # self.fields["progress"].label = "Played Time"
