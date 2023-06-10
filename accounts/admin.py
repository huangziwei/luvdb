from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import InvitationCode

CustomUser = get_user_model()


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Custom admin for users."""

    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ["username", "is_staff", "date_joined", "code_used"]


@admin.register(InvitationCode)
class InvitationCodeAdmin(admin.ModelAdmin):
    """Admin for invitation codes."""

    list_display = ["code", "is_used"]
