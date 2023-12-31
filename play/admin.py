from django.contrib import admin

from .models import (
    Game,
    GameCast,
    GameInSeries,
    GameReleaseDate,
    GameRole,
    GameSeries,
    Genre,
    Platform,
    PlayCheckIn,
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


class GameReleaseDateInline(admin.TabularInline):
    model = GameReleaseDate
    extra = 0


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ["name", "notes", "website", "release_date", "discontinued_date"]
    search_fields = ["name"]


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ["title", "other_titles", "website", "price"]
    search_fields = ["title", "other_titles"]
    inlines = [
        GameReleaseDateInline,
        GameRoleInline,
        GameCastInline,
        GameInSeriesInline,
    ]


@admin.register(GameRole)
class GameRoleAdmin(admin.ModelAdmin):
    list_display = ["game", "creator", "role", "alt_name"]
    search_fields = ["game__title", "creator__name", "role__name"]


@admin.register(GameCast)
class GameCastAdmin(admin.ModelAdmin):
    list_display = ["game", "creator", "role", "character_name"]
    search_fields = ["game__title", "creator__name", "role__name"]


@admin.register(PlayCheckIn)
class PlayCheckInAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "status",
        "progress",
        "content",
        "timestamp",
    ]
    search_fields = ["user__username", "status"]


@admin.register(GameSeries)
class GameSeriesAdmin(admin.ModelAdmin):
    list_display = ["title"]
    search_fields = ["title"]
    inlines = [GameInSeriesInline]


@admin.register(GameInSeries)
class GameInSeriesAdmin(admin.ModelAdmin):
    list_display = ["game", "series", "order"]
    search_fields = ["game__title", "series__title"]


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]
