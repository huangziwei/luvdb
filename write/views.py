from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView

from activity_feed.models import Activity

from .forms import PostForm, SayForm
from .models import Post, Say

User = get_user_model()


class PostListView(ListView):
    model = Post
    template_name = "write/post_list.html"

    def get_queryset(self):
        self.user = get_object_or_404(User, username=self.kwargs["username"])
        return Post.objects.filter(author=self.user)


class PostDetailView(DetailView):
    model = Post
    template_name = "write/post_detail.html"


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    # fields = ["title", "content"]
    template_name = "write/post_form.html"

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("write:post_detail", args=[str(self.object.id)])


class SayListView(ListView):
    model = Say
    template_name = "write/say_list.html"

    def get_queryset(self):
        self.user = get_object_or_404(
            get_user_model(), username=self.kwargs["username"]
        )
        return Say.objects.filter(author=self.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.request.user
        return context


class SayDetailView(DetailView):
    model = Say
    template_name = "write/say_detail.html"


class SayCreateView(LoginRequiredMixin, CreateView):
    model = Say
    form_class = SayForm
    # fields = ["content"]
    template_name = "write/say_form.html"

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("write:say_detail", args=[str(self.object.id)])