from django.contrib import admin

from .models import (
    BlacklistedDomain,
    CustomUser,
    InvitationCode,
    InvitationRequest,
    WebAuthnCredential,
)


class InvitationCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "is_used", "generated_by", "generated_at")


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "display_name", "invited_by", "is_active")


class InvitationRequestAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at", "is_invited", "about_me")


class WebAuthnCredentialAdmin(admin.ModelAdmin):
    list_display = ("user", "aaguid", "public_key", "created_at")


class BlacklistedDomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "created_at")


admin.site.register(InvitationCode, InvitationCodeAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(InvitationRequest, InvitationRequestAdmin)
admin.site.register(WebAuthnCredential, WebAuthnCredentialAdmin)
admin.site.register(BlacklistedDomain, BlacklistedDomainAdmin)
