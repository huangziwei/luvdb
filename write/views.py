from collections import Counter
from itertools import chain

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from django.views.generic.edit import FormView

from activity_feed.models import Activity

from .forms import CommentForm, PinForm, PostForm, RepostForm, SayForm
from .models import Comment, Pin, Post, Repost, Say

User = get_user_model()


class ShareDetailView(DetailView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = Comment.objects.filter(
            content_type=ContentType.objects.get_for_model(self.object),
            object_id=self.object.id,
        )
        context["comment_form"] = CommentForm()
        context["repost_form"] = RepostForm()
        context["app_label"] = self.object._meta.app_label
        context["object_type"] = self.object._meta.model_name.lower()

        return context


class PostListView(ListView):
    model = Post
    template_name = "write/post_list.html"

    def get_queryset(self):
        self.user = get_object_or_404(User, username=self.kwargs["username"])
        return Post.objects.filter(user=self.user).order_by("-timestamp")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.user

        # Get all tags for this user's pins
        all_tags = set()
        for post in Post.objects.filter(user=self.user):
            for tag in post.tags.all():
                all_tags.add(tag)
        context["all_tags"] = all_tags

        return context


class PostDetailView(ShareDetailView):
    model = Post
    template_name = "write/post_detail.html"


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = "write/post_create.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("write:post_detail", args=[str(self.object.id)])


class PostUpdateView(UpdateView):
    model = Post
    template_name = "write/post_update.html"
    form_class = PostForm

    def get_success_url(self):
        return reverse_lazy("write:post_detail", kwargs={"pk": self.object.id})


class PostDeleteView(DeleteView):
    model = Post
    template_name = "write/post_confirm_delete.html"
    success_url = reverse_lazy("activity_feed:activity_feed")


class SayListView(ListView):
    model = Say
    template_name = "write/say_list.html"

    def get_queryset(self):
        self.user = get_object_or_404(
            get_user_model(), username=self.kwargs["username"]
        )
        return Say.objects.filter(user=self.user).order_by("-timestamp")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.user
        return context


class SayDetailView(ShareDetailView):
    model = Say
    template_name = "write/say_detail.html"


class SayCreateView(LoginRequiredMixin, CreateView):
    model = Say
    form_class = SayForm
    # fields = ["content"]
    template_name = "write/say_create.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("write:say_detail", args=[str(self.object.id)])


class SayUpdateView(UpdateView):
    model = Say
    template_name = "write/say_update.html"
    form_class = SayForm

    def get_success_url(self):
        return reverse_lazy("write:say_detail", kwargs={"pk": self.object.id})


class SayDeleteView(DeleteView):
    model = Say
    template_name = "write/say_confirm_delete.html"
    success_url = reverse_lazy("activity_feed:activity_feed")


class PinListView(ListView):
    model = Pin
    template_name = "write/pin_list.html"

    def get_queryset(self):
        self.user = get_object_or_404(
            get_user_model(), username=self.kwargs["username"]
        )
        return Pin.objects.filter(user=self.user).order_by("-timestamp")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.user

        # Get all tags for this user's pins
        all_tags = []
        for pin in Pin.objects.filter(user=self.user):
            for tag in pin.tags.all():
                all_tags.append(tag)

        # Count the frequency of each tag
        tag_counter = Counter(all_tags)

        # Calculate max size limit for tags (200% in this case)
        max_size = 200
        min_size = 100
        max_count = max(tag_counter.values(), default=1)
        scaling_factor = (max_size - min_size) / max_count

        # Scale the counts so that the maximum count corresponds to the maximum size
        tag_sizes = {}
        for tag in tag_counter:
            tag_sizes[tag] = min_size + scaling_factor * tag_counter[tag]

        context["all_tags"] = tag_sizes

        return context


class PinDetailView(ShareDetailView):
    model = Pin
    template_name = "write/pin_detail.html"


class PinCreateView(LoginRequiredMixin, CreateView):
    model = Pin
    form_class = PinForm
    template_name = "write/pin_create.html"

    def get_initial(self):
        initial = super().get_initial()
        original_pin_id = self.kwargs.get("pk")
        if original_pin_id:
            original_pin = get_object_or_404(Pin, pk=original_pin_id)
            initial["title"] = original_pin.title
            initial["url"] = original_pin.url
        return initial

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("write:pin_detail", args=[str(self.object.id)])


class PinUpdateView(UpdateView):
    model = Pin
    template_name = "write/pin_update.html"
    form_class = PinForm

    def get_success_url(self):
        return reverse_lazy("write:pin_detail", kwargs={"pk": self.object.id})


class PinDeleteView(DeleteView):
    model = Pin
    template_name = "write/pin_confirm_delete.html"
    success_url = reverse_lazy("activity_feed:activity_feed")


class PinsFromURLView(ListView):
    model = Pin
    template_name = "write/pins_from_url.html"
    context_object_name = "pins"

    def get_queryset(self):
        root_url = self.kwargs["root_url"]

        # Add the scheme to the root_url if it's not there
        if not root_url.startswith("http"):
            root_url = "http://" + root_url

        # Get all pins with a URL that starts with the root_url
        return Pin.objects.filter(url__startswith=root_url)

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add root_url to the context
        context["root_url"] = self.kwargs["root_url"]
        return context


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = "write/comment_create.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.content_type = ContentType.objects.get(
            app_label=self.kwargs["app_label"], model=self.kwargs["model_name"].lower()
        )
        form.instance.object_id = self.kwargs["object_id"]
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.content_object.get_absolute_url()


class CommentUpdateView(UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = "write/comment_update.html"

    def get_success_url(self):
        return self.object.content_object.get_absolute_url()


class CommentDeleteView(DeleteView):
    model = Comment
    template_name = "write/comment_confirm_delete.html"

    def get_success_url(self):
        return self.object.content_object.get_absolute_url()


class TagListView(ListView):
    template_name = "write/tag_list.html"

    def get_queryset(self):
        tag = self.kwargs["tag"]
        posts = Post.objects.filter(tags__name=tag)
        says = Say.objects.filter(tags__name=tag)
        pins = Pin.objects.filter(tags__name=tag)
        return list(chain(posts, says, pins))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tag = self.kwargs["tag"]
        context["tag"] = tag
        context["posts"] = posts = Post.objects.filter(tags__name=tag)
        context["says"] = says = Say.objects.filter(tags__name=tag)
        context["pins"] = pins = Pin.objects.filter(tags__name=tag)
        context["users"] = User.objects.filter(
            bio__icontains=tag
        )  # these are the users with this tag in their bio
        all_tags = set()
        for obj in chain(posts, says, pins):
            for t in obj.tags.all():
                all_tags.add(t)
        context["all_tags"] = all_tags
        return context


class TagUserListView(ListView):
    template_name = "write/tag_user_list.html"

    def get_queryset(self):
        tag = self.kwargs["tag"]
        username = self.kwargs["username"]
        user = User.objects.get(username=username)
        posts = Post.objects.filter(tags__name=tag, user=user)
        says = Say.objects.filter(tags__name=tag, user=user)
        pins = Pin.objects.filter(tags__name=tag, user=user)
        return list(chain(posts, says, pins))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tag = self.kwargs["tag"]
        username = self.kwargs["username"]
        user = User.objects.get(username=username)
        context["tag"] = tag
        context["user"] = user  # the user whose tags we are viewing
        context["posts"] = posts = Post.objects.filter(tags__name=tag, user=user)
        context["says"] = says = Say.objects.filter(tags__name=tag, user=user)
        context["pins"] = pins = Pin.objects.filter(tags__name=tag, user=user)
        all_tags = set()
        for obj in chain(posts, says, pins):
            for t in obj.tags.all():
                all_tags.add(t)
        context["all_tags"] = all_tags
        return context


class RepostCreateView(LoginRequiredMixin, CreateView):
    model = Repost
    template_name = "write/repost_create.html"
    form_class = RepostForm

    def form_valid(self, form):
        original_activity = get_object_or_404(Activity, id=self.kwargs["activity_id"])
        repost = form.save(commit=False)
        repost.user = self.request.user
        repost.original_activity = original_activity
        repost.content_object = original_activity.content_object
        repost.save()
        return redirect("activity_feed:activity_feed")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["original_activity"] = get_object_or_404(
            Activity, id=self.kwargs["activity_id"]
        )
        return context


class RepostDetailView(ShareDetailView):
    model = Repost
    template_name = "write/repost_detail.html"
    context_object_name = "repost"


class RepostDeleteView(LoginRequiredMixin, DeleteView):
    model = Repost
    template_name = "write/repost_confirm_delete.html"
    success_url = reverse_lazy("activity_feed:activity_feed")


class RepostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Repost
    template_name = "write/repost_update.html"
    form_class = RepostForm

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def test_func(self):
        repost = self.get_object()
        return self.request.user == repost.user
