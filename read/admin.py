from django.contrib import admin

from .models import Book, BookRole, BookWork, Person, Publisher, Role, Work, WorkRole


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


class BookRoleInline(admin.TabularInline):
    model = BookRole
    fields = ("person", "role", "name")
    extra = 1
    autocomplete_fields = ["person"]


class BookWorkInline(admin.TabularInline):
    model = BookWork
    extra = 1


class BookAdmin(admin.ModelAdmin):
    list_display = (
        "book_title",
        "display_works",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    def display_works(self, obj):
        return ", ".join([work.title for work in obj.works.all()])

    display_works.short_description = "Works"

    search_fields = ("book_title",)

    inlines = [BookRoleInline, BookWorkInline]

    autocomplete_fields = ["publisher"]


class RoleAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class WorkRoleAdmin(admin.ModelAdmin):
    list_display = ("work", "person", "role")
    search_fields = ("work__title", "person__name", "role__name")
    list_filter = ("role",)


class BookRoleAdmin(admin.ModelAdmin):
    list_display = ("book", "person", "name", "role")
    list_filter = ("book", "person", "role")
    search_fields = ("book__book_title", "person__name", "role__name")


admin.site.register(Person, PersonAdmin)
admin.site.register(Publisher, PublisherAdmin)
admin.site.register(Work, WorkAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(WorkRole, WorkRoleAdmin)
admin.site.register(BookRole, BookRoleAdmin)
