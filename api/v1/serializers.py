import auto_prefetch
from rest_framework import serializers

from entity.models import Company, Creator, Role
from read.models import Book, BookRole


class CreatorSerializer(serializers.ModelSerializer):
    class Meta(auto_prefetch.Model.Meta):
        model = Creator
        fields = ["id", "name", "other_names"]


class CompanySerializer(serializers.ModelSerializer):
    class Meta(auto_prefetch.Model.Meta):
        model = Company
        fields = ["id", "name", "other_names"]


class RoleSerializer(serializers.ModelSerializer):
    class Meta(auto_prefetch.Model.Meta):
        model = Role
        fields = ["name"]  # include fields you want to display


class BookRoleSerializer(serializers.ModelSerializer):
    creator = CreatorSerializer()
    role = RoleSerializer()

    class Meta(auto_prefetch.Model.Meta):
        model = BookRole
        fields = ["creator", "role", "alt_name"]


class BookSerializer(serializers.ModelSerializer):
    creators = BookRoleSerializer(source="bookrole_set", many=True)
    publisher = CompanySerializer()

    class Meta(auto_prefetch.Model.Meta):
        model = Book
        fields = [
            "id",
            "creators",
            "title",
            "subtitle",
            "publication_date",
            "isbn_10",
            "isbn_13",
            "eisbn_13",
            "asin",
            "language",
            "format",
            "length",
            "cover",
            "cover_sens",
            "publisher",
        ]
