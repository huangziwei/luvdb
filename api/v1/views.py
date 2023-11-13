from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from entity.models import Company, Creator
from read.models import Book

from .serializers import BookSerializer, CompanySerializer, CreatorSerializer


class CreatorViewSetV1(viewsets.ModelViewSet):
    queryset = Creator.objects.all()
    serializer_class = CreatorSerializer
    http_method_names = ["get", "head", "options"]


class CompanyViewSetV1(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    http_method_names = ["get", "head", "options"]


class BookViewSetV1(viewsets.ReadOnlyModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def list(self, request, *args, **kwargs):
        return Response(
            {"detail": "Listing all books is not allowed."},
            status=status.HTTP_403_FORBIDDEN,
        )

    @action(detail=False, methods=["get"], url_path="title/(?P<title>[^/]+)")
    def by_title(self, request, title=None):
        # Split the title parameter on commas
        keywords = title.split(",")

        # Construct the query
        query = Q(title__icontains=keywords[0].strip())
        for keyword in keywords[1:]:
            query &= Q(title__icontains=keyword.strip())  # Using AND condition

        books = Book.objects.filter(query)[:5]
        serializer = self.get_serializer(books, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="isbn10/(?P<isbn10>[^/]+)")
    def by_isbn10(self, request, isbn10=None):
        books = Book.objects.filter(isbn_10=isbn10)
        serializer = self.get_serializer(books, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="isbn13/(?P<isbn13>[^/]+)")
    def by_isbn13(self, request, isbn13=None):
        books = Book.objects.filter(isbn_13=isbn13)
        serializer = self.get_serializer(books, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="eisbn13/(?P<eisbn13>[^/]+)")
    def by_eisbn13(self, request, eisbn13=None):
        books = Book.objects.filter(eisbn_13=eisbn13)
        serializer = self.get_serializer(books, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="asin/(?P<asin>[^/]+)")
    def by_asin(self, request, asin=None):
        books = Book.objects.filter(asin=asin)
        serializer = self.get_serializer(books, many=True)
        return Response(serializer.data)
