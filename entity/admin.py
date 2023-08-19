from django.contrib import admin

from .models import Person, Role


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "other_names",
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
