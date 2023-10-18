from django.contrib import admin

from .models import (
    Book,
    BookInSeries,
    BookInstance,
    BookRole,
    BookSeries,
    Genre,
    Instance,
    InstanceRole,
    Issue,
    IssueInstance,
    Periodical,
    Publisher,
    ReadCheckIn,
    Work,
    WorkRole,
)


class GenreAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class PublisherAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at", "created_by", "updated_by")
    search_fields = ("name",)


class WorkRoleInline(admin.TabularInline):
    model = WorkRole
    extra = 1
    fields = ("creator", "role")
    autocomplete_fields = ["creator"]


class WorkAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "updated_at", "created_by", "updated_by")
    search_fields = ("title",)
    inlines = [WorkRoleInline]


class InstanceRoleInline(admin.TabularInline):
    model = InstanceRole
    extra = 1
    fields = ("creator", "role")
    autocomplete_fields = ["creator"]


class InstanceAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)
    inlines = [InstanceRoleInline]


class BookRoleInline(admin.TabularInline):
    model = BookRole
    fields = ("creator", "role", "alt_name")
    extra = 1
    autocomplete_fields = ["creator"]


class BookInstanceInline(admin.TabularInline):
    model = BookInstance
    extra = 1
    autocomplete_fields = ["instance"]


class BookAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    search_fields = ("title",)

    inlines = [BookRoleInline, BookInstanceInline]  # Changed to new inline

    autocomplete_fields = ["publisher"]


class PeriodicalAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)


class IssueInstanceInline(admin.TabularInline):
    model = IssueInstance
    extra = 1
    autocomplete_fields = ["instance"]


class IssueAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)

    inlines = [IssueInstanceInline]  # Changed to new inline


class WorkRoleAdmin(admin.ModelAdmin):
    list_display = ("work", "creator", "role")
    search_fields = ("work__title", "creator__name", "role__name")
    list_filter = ("role",)


class InstanceRoleAdmin(admin.ModelAdmin):
    list_display = ("instance", "creator", "role")
    search_fields = ("instance__title", "creator__name", "role__name")
    list_filter = ("role",)


class BookRoleAdmin(admin.ModelAdmin):
    list_display = ("book", "creator", "alt_name", "role")
    list_filter = ("book", "creator", "role")
    search_fields = ("book__title", "creator__name", "role__name")


class BookInSeriesInline(admin.TabularInline):
    model = BookInSeries
    extra = 1


class SeriesAdmin(admin.ModelAdmin):
    list_display = ["id", "title"]
    search_fields = ["title"]

    inlines = [BookInSeriesInline]


admin.site.register(Publisher, PublisherAdmin)
admin.site.register(Work, WorkAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(Instance, InstanceAdmin)
admin.site.register(WorkRole, WorkRoleAdmin)
admin.site.register(BookRole, BookRoleAdmin)
admin.site.register(InstanceRole, InstanceRoleAdmin)
admin.site.register(Periodical, PeriodicalAdmin)
admin.site.register(Issue, IssueAdmin)
admin.site.register(BookSeries, SeriesAdmin)
admin.site.register(Genre, GenreAdmin)


@admin.register(ReadCheckIn)
class ReadCheckInAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "status",
        "progress",
        "content",
        "timestamp",
    )
    search_fields = ("user__username", "content")
    list_filter = ("status", "timestamp")
