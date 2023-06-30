# Register your models here.
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


class LabelAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at", "created_by", "updated_by")
    search_fields = ("name",)


class ListenCheckInAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "timestamp")
    search_fields = ("user__username", "status")


class ReleaseRoleInline(admin.TabularInline):
    model = ReleaseRole
    extra = 1
    fields = ("person", "role")
    autocomplete_fields = ["person"]


class ReleaseTrackInline(admin.TabularInline):
    model = ReleaseTrack
    extra = 1
    fields = ("track", "order")
    autocomplete_fields = ["track"]


class ReleaseAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "updated_at", "created_by", "updated_by")
    search_fields = ("title",)

    inlines = [ReleaseRoleInline, ReleaseTrackInline]


class TrackRoleInline(admin.TabularInline):
    model = TrackRole
    extra = 1
    fields = ("person", "role")
    autocomplete_fields = ["person"]


class TrackAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "updated_at", "created_by", "updated_by")
    search_fields = ("title",)
    inlines = [TrackRoleInline]


class WorkRoleInline(admin.TabularInline):
    model = WorkRole
    extra = 1
    fields = ("person", "role")
    autocomplete_fields = ["person"]


class WorkAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)
    inlines = [WorkRoleInline]


admin.site.register(ListenCheckIn, ListenCheckInAdmin)
admin.site.register(Label, LabelAdmin)
admin.site.register(Release, ReleaseAdmin)
admin.site.register(Track, TrackAdmin)
admin.site.register(Work, WorkAdmin)
