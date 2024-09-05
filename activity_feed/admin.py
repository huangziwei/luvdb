from django.contrib import admin

from .models import Activity, Block, Follow


class ActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "activity_type", "timestamp", "get_content_object_display")
    list_filter = ("timestamp",)

    def get_content_object_display(self, obj):
        # Check if content_object has 'content' field (specific to Say or similar objects)
        if hasattr(obj.content_object, "content"):
            return obj.content_object.content[:300]
        # Fallback if content_object doesn't have 'content' attribute
        return obj

    # Change the column header in the list display
    get_content_object_display.short_description = "Activity Content"


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
