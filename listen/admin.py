from django.contrib import admin

from .models import (
    Label,
    ListenCheckIn,
    Release,
    ReleaseRole,
    ReleaseTrack,
    Track,
    TrackRole,
    Work,
    WorkRole,
)


class WorkRoleInline(admin.TabularInline):
    model = WorkRole
    extra = 1


class WorkAdmin(admin.ModelAdmin):
    list_display = ["title", "release_date", "genre"]
    inlines = [WorkRoleInline]


class TrackRoleInline(admin.TabularInline):
    model = TrackRole
    extra = 1


class TrackAdmin(admin.ModelAdmin):
    list_display = ["title", "release_date", "length", "genre"]
    inlines = [TrackRoleInline]


class ReleaseRoleInline(admin.TabularInline):
    model = ReleaseRole
    extra = 1


class ReleaseTrackInline(admin.TabularInline):
    model = ReleaseTrack
    extra = 1


class ReleaseAdmin(admin.ModelAdmin):
    list_display = ["title", "release_date", "genre", "release_type", "release_format"]
    inlines = [ReleaseRoleInline, ReleaseTrackInline]


admin.site.register(Label)
admin.site.register(Work, WorkAdmin)
admin.site.register(Track, TrackAdmin)
admin.site.register(Release, ReleaseAdmin)
admin.site.register(ListenCheckIn)
