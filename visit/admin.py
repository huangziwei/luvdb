from django.contrib import admin

# Register your models here.
from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "level",
        "parent",
        "historical",
    ]
    search_fields = [
        "name",
        "other_names",
        "level",
        "parent",
        "historical",
        "historical_period",
        "address",
        "notes",
    ]
    list_filter = ["level", "parent", "historical", "historical_period"]
