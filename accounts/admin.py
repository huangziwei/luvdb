from django.contrib import admin

from .models import CustomUser, InvitationCode


class InvitationCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "is_used", "generated_by", "generated_at")


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "display_name", "invited_by")


admin.site.register(InvitationCode, InvitationCodeAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
