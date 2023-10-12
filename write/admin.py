from django.contrib import admin

from .models import Category, Comment, ContentInList, LuvList, Pin, Post, Repost, Say


class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)


class PostAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "content", "timestamp")


class SayAdmin(admin.ModelAdmin):
    list_display = ("user", "content", "timestamp")


class PinAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "url", "content", "timestamp")


class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "content_type", "content", "timestamp")


class RepostAdmin(admin.ModelAdmin):
    list_display = ("user", "content", "original_activity", "timestamp")


class ContentInListInline(admin.TabularInline):
    model = ContentInList
    extra = 1  # How many rows to show for new entries


class LuvListAdmin(admin.ModelAdmin):
    inlines = [ContentInListInline]


admin.site.register(LuvList, LuvListAdmin)
admin.site.register(Repost, RepostAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Pin, PinAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Say, SayAdmin)
admin.site.register(Category, CategoryAdmin)
