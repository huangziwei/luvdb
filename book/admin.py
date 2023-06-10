from django.contrib import admin

from .models import Book, Edition, Person, Publisher, Series

# Register your models here.

admin.site.register(Book)
admin.site.register(Person)
admin.site.register(Publisher)
admin.site.register(Series)
admin.site.register(Edition)

# Add more admin models as needed.
