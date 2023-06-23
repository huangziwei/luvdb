# Register your models here.
from django.contrib import admin

from .models import Developer, Game, GameCheckIn, GameRole, Platform


class GameAdmin(admin.ModelAdmin):
    list_display = ("title", "release_date", "created_by", "updated_by")
    search_fields = ("title", "description")
    filter_horizontal = ("developers", "persons", "platforms")


class GameRoleAdmin(admin.ModelAdmin):
    list_display = ("game", "person", "role")
    search_fields = ("game__title", "person__name", "role__name")


class GameCheckInAdmin(admin.ModelAdmin):
    list_display = ("game", "user", "status", "timestamp")
    search_fields = ("game__title", "user__username", "status")


class DeveloperAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "founded_date", "closed_date")
    search_fields = ("name", "location")


class PlatformAdmin(admin.ModelAdmin):
    list_display = ("name", "release_date", "discontinued_date")
    search_fields = ("name", "release_date")


admin.site.register(Game, GameAdmin)
admin.site.register(GameRole, GameRoleAdmin)
admin.site.register(GameCheckIn, GameCheckInAdmin)
admin.site.register(Developer, DeveloperAdmin)
admin.site.register(Platform, PlatformAdmin)
