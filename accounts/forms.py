import auto_prefetch
import pytz
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    PasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)
from django.utils.safestring import mark_safe

from .models import (
    AppPassword,
    BlueSkyAccount,
    CustomUser,
    InvitationCode,
    InvitationRequest,
    MastodonAccount,
    WebAuthnCredential,
)

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Form for user creation with invitation code."""

    invitation_code = forms.CharField(
        required=True,
        help_text="Enter the invitation code you received. Or, <a href='/login'>request one</a>.",
    )
    SIGNUP_CHOICES = (
        ("password", "Password Only"),
        ("passkey", "Passkey Only"),
        ("both", "Both Password and Passkey"),
    )

    signup_method = forms.ChoiceField(
        choices=SIGNUP_CHOICES, label="Authentication Method", initial="password"
    )

    class Meta(auto_prefetch.Model.Meta):
        model = User
        fields = ("username", "invitation_code", "signup_method")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = "It can be changed later."
        self.fields["signup_method"].help_text = "placeholder"

    def clean(self):
        cleaned_data = super().clean()
        signup_method = cleaned_data.get("signup_method")

        # If "Passkey Only" is selected, skip password field validation
        if signup_method == "passkey":
            if "password1" in self.errors:
                del self.errors["password1"]
            if "password2" in self.errors:
                del self.errors["password2"]
            cleaned_data["password1"] = User.objects.make_random_password()
            cleaned_data["password2"] = cleaned_data["password1"]
        return cleaned_data

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
        signup_method = self.cleaned_data.get("signup_method")
        if signup_method == "passkey":
            # Generate a secure, random password for the user only if passkey is chosen
            user.set_password(User.objects.make_random_password())

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

    class Meta(auto_prefetch.Model.Meta):
        model = User
        fields = (
            "username",
            "display_name",
            "bio",
            "timezone",
            "enable_replies_by_default",
            "enable_share_to_feed_by_default",
            "is_public",
            "pure_text_mode",
            "enable_alt_profile",
            # "custom_domain",
        )
        help_texts = {
            "username": "Required. Letters, digits and ./+/-/_ only.",
            "display_name": "Display name can be in any language, and can contain emojis.",
            "is_public": "When enabled, your profile becomes publicly accessible, including to non-logged-in users, and activates RSS feeds. Disabling it requires a login to access the profile and list views of Say, Post, Pin, List, and Check-ins. However, the detail views of all contents remain accessible via direct URLs even when this option is turned off.",
            "pure_text_mode": "Enable this option to disable displaying images of the site.",
            "timezone": "Set your preferred timezone. This will adjust the display of all timestamps to match your local date and time.",
            "enable_alt_profile": "Enable this option to activate your alternative profile (`luvdb.com/alt/@username`).",
            # "custom_domain": "Set your custom domain for your alternative profile. Add a CNAME record to your DNS settings to point to `luvdb.com`.",
            "enable_replies_by_default": "Enable this option to allow replies to your posts by default.",
            "enable_share_to_feed_by_default": "Enable this option to allow sharing your posts to your feed by default.",
        }

    def __init__(self, *args, **kwargs):
        super(CustomUserChangeForm, self).__init__(*args, **kwargs)
        self.fields["is_public"].label = "Everyone can view my profile"
        self.fields["pure_text_mode"].label = "Don't display images"
        self.fields["timezone"].required = False
        self.fields["enable_alt_profile"].label = (
            "Enable alternative profile (experimental)"
        )
        self.fields["enable_replies_by_default"].label = "Allow replies by default"
        self.fields["enable_share_to_feed_by_default"].label = (
            "Share to feed by default"
        )

        del self.fields["password"]


class InvitationRequestForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = InvitationRequest
        fields = ["email", "about_me"]
        widgets = {
            "email": forms.TextInput(attrs={"placeholder": "Email Address"}),
            "about_me": forms.Textarea(
                attrs={
                    "placeholder": "Tell us more about you, and why you want to join."
                }
            ),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        # Check if the user has any passkeys
        self.passkeys_exist = WebAuthnCredential.objects.filter(
            user=self.request.user
        ).exists()
        self.is_first_login = self.request.session.get("is_first_login", False)
        if self.passkeys_exist or self.is_first_login:
            # Make old_password not required
            self.fields["old_password"].required = False

    def clean_old_password(self):
        # Check if old_password is actually required before cleaning it
        if self.fields["old_password"].required:
            return super().clean_old_password()

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get("old_password")

        # Skip the old password check if passkeys exist or it's the first login
        if self.passkeys_exist or self.is_first_login:
            # Optionally, you might want to clear any error that might have been added
            # to the old_password field due to form validation mechanisms.
            self._errors.pop("old_password", None)
            return cleaned_data

        # If old_password is required but not provided, raise a validation error
        if not self.passkeys_exist and not self.is_first_login and not old_password:
            self.add_error("old_password", "This field is required.")
        return cleaned_data


class AppPasswordForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = AppPassword
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "App Password Name"}),
        }


class BlueSkyAccountForm(forms.ModelForm):
    bluesky_app_password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="You can get this from your BlueSky account settings. Specifically, go to Settings > App Passwords.",
        label="App Password",
    )

    class Meta(auto_prefetch.Model.Meta):
        model = BlueSkyAccount
        fields = ["bluesky_handle", "bluesky_pds_url", "bluesky_app_password"]
        help_texts = {
            "bluesky_handle": "e.g. handle.bsky.social or yourwebsite.com",
            "bluesky_pds_url": "URL of your Personal Data Server (PDS), e.g. https://bsky.social",
        }
        labels = {
            "bluesky_handle": "Handle",
            "bluesky_pds_url": "PDS URL",
        }

    def clean_bluesky_handle(self):
        # Get the bluesky handle
        bluesky_handle = self.cleaned_data.get("bluesky_handle", "")

        # Remove leading '@' if present
        bluesky_handle = bluesky_handle.lstrip("@")

        return bluesky_handle

    def save(self, user, commit=True):
        bluesky_account = super().save(commit=False)
        bluesky_account.user = user
        bluesky_account.set_bluesky_app_password(
            self.cleaned_data["bluesky_app_password"]
        )
        if commit:
            bluesky_account.save()
        return bluesky_account


class MastodonAccountForm(forms.ModelForm):
    mastodon_access_token = forms.CharField(
        widget=forms.PasswordInput,
        label="Access Token",
        help_text="You can get this from your Mastodon account settings. Specifically, go to Preferences > Development > New application.",
    )

    class Meta(auto_prefetch.Model.Meta):
        model = MastodonAccount
        fields = ["mastodon_handle", "mastodon_access_token"]
        labels = {
            "mastodon_handle": "Handle",
        }
        help_texts = {
            "mastodon_handle": "Your mastodon handle, e.g. yourhandle@mastodon.social",
        }

    def clean_mastodon_handle(self):
        # Get the mastodon handle
        mastodon_handle = self.cleaned_data.get("mastodon_handle", "")

        # Remove leading '@' if present
        mastodon_handle = mastodon_handle.lstrip("@")

        return mastodon_handle

    def save(self, user, commit=True):
        mastodon_account = super().save(commit=False)
        mastodon_account.user = user
        mastodon_account.set_mastodon_access_token(
            self.cleaned_data["mastodon_access_token"]
        )
        if commit:
            mastodon_account.save()
        return mastodon_account
