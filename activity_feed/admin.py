from django.contrib import admin

from .models import Activity, Block, Follow


class ActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "activity_type", "timestamp")
    list_filter = ("timestamp",)


class FollowAdmin(admin.ModelAdmin):
    list_display = (
        "follower",
        "followed",
        "timestamp",
    )
    list_filter = ("timestamp",)


class BlockAdmin(admin.ModelAdmin):
    list_display = (
        "blocker",
        "blocked",
        "timestamp",
    )
    list_filter = ("timestamp",)


# Register your models here.
admin.site.register(Activity, ActivityAdmin)
admin.site.register(Follow, FollowAdmin)
admin.site.register(Block, BlockAdmin)
