import pytz
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import CustomUser, InvitationCode

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Form for user creation with invitation code."""

    invitation_code = forms.CharField(
        required=True, help_text="Enter the invitation code you received"
    )

    class Meta:
        model = User
        fields = ("username", "invitation_code")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = (
            "You can change it later. For anonymity purpose, we don't even record your email address. "
            "But if you forget your username and password, you won't be able to recover it. "
            "Please mark down your username and password somewhere safe."
        )

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username in CustomUser.RESERVED_USERNAMES:
            raise forms.ValidationError(
                "This username is reserved and cannot be registered."
            )
        return username

    def clean_invitation_code(self):
        code = self.cleaned_data.get("invitation_code")
        try:
            invitation = InvitationCode.objects.get(code=code)
            if invitation.is_used:
                raise forms.ValidationError(
                    "This invitation code has already been used."
                )
        except InvitationCode.DoesNotExist:
            raise forms.ValidationError(
                "The invitation code you entered does not exist."
            )
        return invitation

    def save(self, commit=True):
        user = super().save(commit=False)
        invitation = self.mark_invitation_code_as_used(user)
        if invitation.generated_by:
            user.invited_by = invitation.generated_by
        if commit:
            user.save()
        return user

    def mark_invitation_code_as_used(self, user):
        """Marks the invitation code as used and associates it with the user."""
        user.code_used = self.cleaned_data.get("invitation_code")
        user.code_used.is_used = True
        user.code_used.save()
        return user.code_used


class CustomUserChangeForm(UserChangeForm):
    timezone = forms.ChoiceField(choices=[(tz, tz) for tz in pytz.all_timezones])

    class Meta:
        model = User
        fields = ("display_name", "username", "bio", "is_public", "timezone")
        help_texts = {
            "is_public": "Turn on to make your profile public. If not, non-logged-in users won't be able to see your profile.",
        }

    def __init__(self, *args, **kwargs):
        super(CustomUserChangeForm, self).__init__(*args, **kwargs)
        del self.fields["password"]
