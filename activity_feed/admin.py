from django.contrib import admin

from .models import Activity, Follow


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


# Register your models here.
admin.site.register(Activity, ActivityAdmin)
admin.site.register(Follow, FollowAdmin)
