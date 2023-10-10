from django.contrib import admin

from .models import Vote


class VoteAdmin(admin.ModelAdmin):
    list_display = ("user", "content_type", "object_id", "value", "timestamp")
    list_filter = ("content_type", "value")
    search_fields = ("user__username", "object_id", "content_type__model")
    ordering = ("-timestamp",)
    readonly_fields = ("timestamp",)

    fieldsets = (
        (
            "Vote Information",
            {"fields": ("user", "content_type", "object_id", "value", "timestamp")},
        ),
    )


admin.site.register(Vote, VoteAdmin)
