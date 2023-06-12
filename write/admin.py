from django.contrib import admin

from .models import Comment, Pin, Post, Say


class PostAdmin(admin.ModelAdmin):
    list_display = ("author", "title", "content", "timestamp")


class SayAdmin(admin.ModelAdmin):
    list_display = ("author", "content", "timestamp")


class PinAdmin(admin.ModelAdmin):
    list_display = ("author", "title", "url", "content", "timestamp")


class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "content", "timestamp")


admin.site.register(Comment, CommentAdmin)
admin.site.register(Pin, PinAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Say, SayAdmin)
