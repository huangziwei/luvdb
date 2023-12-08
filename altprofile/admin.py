from django.contrib import admin

from .models import AltProfile, AltProfileTemplate


@admin.register(AltProfile)
class AltProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "custom_html", "custom_css")  # Customize as needed
    search_fields = ["user__username"]  # Allows searching by username


@admin.register(AltProfileTemplate)
class AltProfileTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "html_content", "css_content")
    search_fields = ["name"]
