from django.contrib import admin

from .models import Post, Say


class PostAdmin(admin.ModelAdmin):
    list_display = ("author", "title", "content", "timestamp")


class SayAdmin(admin.ModelAdmin):
    list_display = ("author", "content", "timestamp")


admin.site.register(Post, PostAdmin)
admin.site.register(Say, SayAdmin)
