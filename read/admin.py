from django.contrib import admin

from .models import Book, BookRole, Edition, EditionRole, Person, Publisher, Role


class PersonAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at", "created_by", "updated_by")
    search_fields = ("name",)


class PublisherAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at", "created_by", "updated_by")
    search_fields = ("name",)


class BookRoleInline(admin.TabularInline):
    model = BookRole
    extra = 1
    fields = ("person", "role")
    autocomplete_fields = ["person"]


class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "updated_at", "created_by", "updated_by")
    search_fields = ("title",)
    inlines = [BookRoleInline]


class EditionRoleInline(admin.TabularInline):
    model = EditionRole
    fields = ("person", "role", "name")
    extra = 1
    autocomplete_fields = ["person"]


class EditionAdmin(admin.ModelAdmin):
    list_display = (
        "edition_title",
        "book",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )
    search_fields = ("book__title",)
    inlines = [EditionRoleInline]
    autocomplete_fields = ["book", "publisher"]


class RoleAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class BookRoleAdmin(admin.ModelAdmin):
    list_display = ("book", "person", "role")
    search_fields = ("book__title", "person__name", "role__name")
    list_filter = ("role",)


class EditionRoleAdmin(admin.ModelAdmin):
    list_display = ("edition", "person", "name", "role")
    list_filter = ("edition", "person", "role")
    search_fields = ("edition__edition_title", "person__name", "role__name")


admin.site.register(Person, PersonAdmin)
admin.site.register(Publisher, PublisherAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(Edition, EditionAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(BookRole, BookRoleAdmin)
admin.site.register(EditionRole, EditionRoleAdmin)
