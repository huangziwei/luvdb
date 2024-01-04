from django.views.generic import DetailView

from .models import Page


# Create your views here.
class PageDetailView(DetailView):
    model = Page
    template_name = "pages/page_detail.html"
    context_object_name = "page"
