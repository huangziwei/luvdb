from django.contrib import admin

from .models import Company, Creator, Role


@admin.register(Creator)
class PersonAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "other_names",
        "creator_type",
        "birth_date",
        "death_date",
        "birth_place",
        "death_place",
        "wikipedia",
        "website",
    ]
    search_fields = [
        "name",
        "other_names",
        "creator_type",
        "birth_date",
        "death_date",
        "birth_place",
        "death_place",
        "wikipedia",
        "website",
    ]
    list_filter = ["birth_date", "death_date"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "domain"]
    search_fields = ["name", "domain"]
    list_filter = ["domain"]


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name", "location", "website", "wikipedia"]
    search_fields = ["name", "location", "website"]
    list_filter = ["location"]
