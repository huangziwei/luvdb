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
        "wikipedia",
        "website",
    ]
    search_fields = [
        "name",
        "other_names",
        "creator_type",
        "birth_date",
        "death_date",
        "wikipedia",
        "website",
    ]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "domain", "category"]
    search_fields = ["name", "domain"]
    list_filter = ["domain"]


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name", "website", "wikipedia"]
    search_fields = ["name", "website"]
