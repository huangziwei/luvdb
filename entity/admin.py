from django.contrib import admin

from .models import Company, CoverAlbum, CoverImage, Creator, Role


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



class CoverImageInline(admin.TabularInline):
    """
    Inline admin for CoverImage, allowing multiple images to be added to CoverAlbum.
    """
    model = CoverImage
    extra = 1
    fields = ("image", "is_primary", "uploaded_at")
    readonly_fields = ("uploaded_at",)
    ordering = ("-is_primary", "uploaded_at")


@admin.register(CoverAlbum)
class CoverAlbumAdmin(admin.ModelAdmin):
    """
    Admin view for CoverAlbum.
    """
    list_display = ("id", "get_model_name", "get_instance_name", "created_at")
    search_fields = ("object_id",)
    inlines = [CoverImageInline]

    def get_model_name(self, obj):
        """
        Display the related model name (e.g., Book, Movie, Game, Release).
        """
        return obj.content_type.model_class().__name__

    get_model_name.short_description = "Model"

    def get_instance_name(self, obj):
        """
        Display the instance's string representation.
        """
        instance = obj.content_object
        return str(instance) if instance else "N/A"

    get_instance_name.short_description = "Instance"
