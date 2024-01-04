from django.contrib import admin

# Register your models here.
from .models import Page


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "published", "created_at", "updated_at")
    list_filter = ("published", "created_at", "updated_at")
    search_fields = ("title", "content")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-updated_at",)
