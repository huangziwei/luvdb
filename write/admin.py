from django.contrib import admin

from .models import (
    Comment,
    ContentInList,
    LuvList,
    Pin,
    Post,
    Project,
    Repost,
    Say,
    WebMention,
)


class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "name",
        "order",
    )


class PostAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "timestamp", "updated_at", "slug")


class SayAdmin(admin.ModelAdmin):
    list_display = ("user", "content", "timestamp", "updated_at")


class PinAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "url", "content", "timestamp", "updated_at")


class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "content_type", "content", "timestamp", "updated_at")


class RepostAdmin(admin.ModelAdmin):
    list_display = ("user", "content", "original_activity", "timestamp", "updated_at")


class ContentInListInline(admin.TabularInline):
    model = ContentInList
    extra = 1  # How many rows to show for new entries


class LuvListAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "timestamp", "updated_at")
    inlines = [ContentInListInline]


class WebMentionAdmin(admin.ModelAdmin):
    list_display = ("source", "target", "received_at")


admin.site.register(LuvList, LuvListAdmin)
admin.site.register(Repost, RepostAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Pin, PinAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Say, SayAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(WebMention, WebMentionAdmin)
