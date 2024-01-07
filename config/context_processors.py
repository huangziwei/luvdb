from django.urls import reverse

from pages.models import Page

from .version import VERSION


def version_context(request):
    return {"version": VERSION}


def footer_links(request):
    # Fetch all published pages
    pages = Page.objects.filter(published=True)

    # Create a list of tuples (title, URL) for each page
    page_links = [
        (page.title, reverse("pages:page", args=[page.slug])) for page in pages
    ]

    return {
        "page_links": page_links,
    }
