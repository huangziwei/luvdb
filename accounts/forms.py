from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Permission

from .models import InvitationCode

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Form for user creation with invitation code."""

    invitation_code = forms.CharField(required=True)
    invitation_code.help_text = "Enter the invitation code you received"

    class Meta:
        model = User
        fields = ("username", "invitation_code")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[
            "username"
        ].help_text = "Modify your username if you want. For anonymity purpose, we don't record your email address, so you can't reset your password if you forget your username and password. Please write down your username and password somewhere safe."

    def clean_invitation_code(self):
        code = self.cleaned_data.get("invitation_code")
        # If not, check if it's a valid invitation code
        try:
            invitation = InvitationCode.objects.get(code=code)
            if invitation.is_used:
                raise forms.ValidationError(
                    "This invitation code has already been used"
                )
        except InvitationCode.DoesNotExist:
            raise forms.ValidationError("The code you entered is incorrect")
        return invitation  # Return the invitation instance, not the code

    def save(self, commit=True):
        user = super().save(commit=False)
        user.code_used = self.cleaned_data.get(
            "invitation_code"
        )  # This will be an InvitationCode instance now
        user.code_used.is_used = True
        user.code_used.save()

        if commit:
            user.save()

        return user


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ("display_name", "username", "bio")
