from django.contrib import admin

from .models import (
    Developer,
    Game,
    GameCast,
    GameCheckIn,
    GameInSeries,
    GameRole,
    GameSeries,
    Platform,
)


class GameRoleInline(admin.TabularInline):
    model = GameRole
    extra = 0


class GameCastInline(admin.TabularInline):
    model = GameCast
    extra = 0


class GameInSeriesInline(admin.TabularInline):
    model = GameInSeries
    extra = 0


@admin.register(Developer)
class DeveloperAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "history",
        "location",
        "website",
        "founded_date",
        "closed_date",
    ]
    search_fields = ["name"]


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ["name", "history", "website", "release_date", "discontinued_date"]
    search_fields = ["name"]


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ["title", "romanized_title", "release_date", "website", "price"]
    search_fields = ["title", "romanized_title"]
    inlines = [GameRoleInline, GameCastInline, GameInSeriesInline]


@admin.register(GameRole)
class GameRoleAdmin(admin.ModelAdmin):
    list_display = ["game", "person", "role", "alt_name"]
    search_fields = ["game__title", "person__name", "role__name"]


@admin.register(GameCast)
class GameCastAdmin(admin.ModelAdmin):
    list_display = ["game", "person", "role", "character_name"]
    search_fields = ["game__title", "person__name", "role__name"]


@admin.register(GameCheckIn)
class GameCheckInAdmin(admin.ModelAdmin):
    list_display = ["game", "user", "status", "timestamp", "progress", "progress_type"]
    search_fields = ["game__title", "user__username", "status"]


@admin.register(GameSeries)
class GameSeriesAdmin(admin.ModelAdmin):
    list_display = ["title"]
    search_fields = ["title"]
    inlines = [GameInSeriesInline]


@admin.register(GameInSeries)
class GameInSeriesAdmin(admin.ModelAdmin):
    list_display = ["game", "series", "order"]
    search_fields = ["game__title", "series__title"]
