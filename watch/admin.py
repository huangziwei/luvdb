from django.contrib import admin

from .models import (
    Episode,
    EpisodeCast,
    EpisodeRole,
    Genre,
    Movie,
    MovieCast,
    MovieRole,
    Series,
    SeriesRole,
    Studio,
    WatchCheckIn,
)


class MovieRoleInline(admin.TabularInline):
    model = MovieRole
    extra = 1


class MovieCastInline(admin.TabularInline):
    model = MovieCast
    extra = 1


class SeriesRoleInline(admin.TabularInline):
    model = SeriesRole
    extra = 1


class EpisodeRoleInline(admin.TabularInline):
    model = EpisodeRole
    extra = 1


class EpisodeCastInline(admin.TabularInline):
    model = EpisodeCast
    extra = 1


class MovieAdmin(admin.ModelAdmin):
    inlines = (MovieRoleInline, MovieCastInline)
    list_display = ("title", "release_date")
    search_fields = ["title"]
    list_filter = ["release_date"]


class SeriesAdmin(admin.ModelAdmin):
    inlines = (SeriesRoleInline,)
    list_display = ("title", "release_date")
    search_fields = ["title"]
    list_filter = ["release_date"]


class EpisodeAdmin(admin.ModelAdmin):
    inlines = (EpisodeRoleInline, EpisodeCastInline)
    list_display = ("series", "title", "season", "episode", "release_date")
    search_fields = ["title", "series__title"]
    list_filter = ["release_date", "series"]


class WatchCheckInAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "timestamp")
    search_fields = ["user__username", "status"]
    list_filter = ["status", "timestamp"]


class GenreAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ["name"]


class StudioAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ["name"]


admin.site.register(Genre, GenreAdmin)
admin.site.register(Movie, MovieAdmin)
admin.site.register(Studio, StudioAdmin)
admin.site.register(Series, SeriesAdmin)
admin.site.register(Episode, EpisodeAdmin)
admin.site.register(WatchCheckIn, WatchCheckInAdmin)
