from django.contrib import admin

from .models import (
    Book,
    BookCheckIn,
    BookRole,
    Edition,
    EditionRole,
    Issue,
    Periodical,
    Person,
    Publisher,
    Role,
    Work,
    WorkRole,
)


class PersonAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at", "created_by", "updated_by")
    search_fields = ("name",)


class PublisherAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at", "created_by", "updated_by")
    search_fields = ("name",)


class WorkRoleInline(admin.TabularInline):
    model = WorkRole
    extra = 1
    fields = ("person", "role")
    autocomplete_fields = ["person"]


class WorkAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "updated_at", "created_by", "updated_by")
    search_fields = ("title",)
    inlines = [WorkRoleInline]


class EditionRoleInline(admin.TabularInline):
    model = EditionRole
    extra = 1
    fields = ("person", "role")
    autocomplete_fields = ["person"]


class EditionAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)
    inlines = [EditionRoleInline]


class BookRoleInline(admin.TabularInline):
    model = BookRole
    fields = ("person", "role", "alt_name")
    extra = 1
    autocomplete_fields = ["person"]


class BookAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    search_fields = ("title",)

    inlines = [BookRoleInline]  # Changed to new inline

    autocomplete_fields = ["publisher"]


class PeriodicalAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)


class IssueAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)


class RoleAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class WorkRoleAdmin(admin.ModelAdmin):
    list_display = ("work", "person", "role")
    search_fields = ("work__title", "person__name", "role__name")
    list_filter = ("role",)


class EditionRoleAdmin(admin.ModelAdmin):
    list_display = ("edition", "person", "role")
    search_fields = ("edition__title", "person__name", "role__name")
    list_filter = ("role",)


class BookRoleAdmin(admin.ModelAdmin):
    list_display = ("book", "person", "alt_name", "role")
    list_filter = ("book", "person", "role")
    search_fields = ("book__title", "person__name", "role__name")


admin.site.register(Person, PersonAdmin)
admin.site.register(Publisher, PublisherAdmin)
admin.site.register(Work, WorkAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(Edition, EditionAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(WorkRole, WorkRoleAdmin)
admin.site.register(BookRole, BookRoleAdmin)
admin.site.register(EditionRole, EditionRoleAdmin)
admin.site.register(Periodical, PeriodicalAdmin)
admin.site.register(Issue, IssueAdmin)


@admin.register(BookCheckIn)
class BookCheckInAdmin(admin.ModelAdmin):
    list_display = ("book", "user", "status", "progress", "content", "timestamp")
    search_fields = ("book__title", "user__username", "content")
    list_filter = ("status", "timestamp")
