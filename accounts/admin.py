from django.contrib import admin

from .models import CustomUser, FediverseFollower, InvitationCode, InvitationRequest


class InvitationCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "is_used", "generated_by", "generated_at")


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "display_name", "invited_by")


class InvitationRequestAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at", "is_invited", "about_me")


class FediverseFollowerAdmin(admin.ModelAdmin):
    list_display = ("user", "follower_uri")
    search_fields = ("user__username", "follower_uri")
    list_filter = ("user",)
    ordering = ("user", "follower_uri")
    fieldsets = ((None, {"fields": ("user", "follower_uri")}),)


admin.site.register(FediverseFollower, FediverseFollowerAdmin)
admin.site.register(InvitationCode, InvitationCodeAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(InvitationRequest, InvitationRequestAdmin)
