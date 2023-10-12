import random
from collections import Counter
from datetime import timedelta
from itertools import chain
from operator import attrgetter

import pytz
from dal import autocomplete
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from activity_feed.models import Activity
from discover.views import user_has_upvoted
from listen.models import ListenCheckIn
from play.models import GameCheckIn
from read.models import ReadCheckIn
from watch.models import WatchCheckIn

from .forms import (
    CommentForm,
    ContentInListFormSet,
    LuvListForm,
    PinForm,
    PostForm,
    RepostForm,
    SayForm,
)
from .models import (
    Category,
    Comment,
    ContentInList,
    LuvList,
    Pin,
    Post,
    Randomizer,
    Repost,
    Say,
)

User = get_user_model()


class ShareDetailView(DetailView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comments"] = (
            Comment.objects.filter(
                content_type=ContentType.objects.get_for_model(self.object),
                object_id=self.object.id,
            )
            .order_by("timestamp")
            .order_by("timestamp")
        )
        context["comment_form"] = CommentForm()
        context["repost_form"] = RepostForm()
        context["app_label"] = self.object._meta.app_label
        context["object_type"] = self.object._meta.model_name.lower()

        return context


class PostListView(ListView):
    model = Post
    template_name = "write/post_list.html"

    def dispatch(self, request, *args, **kwargs):
        # Get the User object
        self.user = get_object_or_404(
            get_user_model(), username=self.kwargs["username"]
        )

        # If the user's profile isn't public and the current user isn't authenticated, raise a 404 error
        if not self.user.is_public and not request.user.is_authenticated:
            return redirect("{}?next={}".format(reverse("login"), request.path))

        # Otherwise, proceed as normal
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        self.user = get_object_or_404(User, username=self.kwargs["username"])
        queryset = Post.objects.filter(user=self.user)

        if "category" in self.kwargs:
            category = Category.objects.filter(
                name=self.kwargs["category"], post__user=self.user
            ).first()
            if category is not None:
                queryset = queryset.filter(categories=category)
            else:
                # Handle the case when the category does not exist
                queryset = Post.objects.none()
        else:
            queryset = queryset.filter(categories__isnull=True)

        return queryset.order_by("-timestamp")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.user

        # Get all tags for this user's pins
        all_tags = []
        for post in Post.objects.filter(user=self.user):
            for tag in post.tags.all():
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
        context["all_categories"] = Category.objects.filter(
            post__user=self.user
        ).distinct()
        context["current_category"] = self.kwargs.get("category", None)

        return context


class PostDetailView(ShareDetailView):
    model = Post
    template_name = "write/post_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_voted"] = user_has_upvoted(self.request.user, self.object)
        context["categories"] = self.object.categories.all()
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = "write/post_create.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("write:post_detail", args=[str(self.object.id)])


class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    template_name = "write/post_update.html"
    form_class = PostForm

    def get_success_url(self):
        return reverse_lazy("write:post_detail", kwargs={"pk": self.object.id})


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = "write/post_confirm_delete.html"
    success_url = reverse_lazy("activity_feed:activity_feed")


class SayListView(ListView):
    model = Say
    template_name = "write/say_list.html"

    def dispatch(self, request, *args, **kwargs):
        # Get the User object
        self.user = get_object_or_404(
            get_user_model(), username=self.kwargs["username"]
        )

        # If the user's profile isn't public and the current user isn't authenticated, raise a 404 error
        if not self.user.is_public and not request.user.is_authenticated:
            return redirect("{}?next={}".format(reverse("login"), request.path))

        # Otherwise, proceed as normal
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        if self.request.user.is_authenticated:
            say_queryset = (
                Say.objects.filter(user=self.user)
                .filter(Q(visible_to=self.request.user) | Q(is_direct_mention=False))
                .order_by("-timestamp")
            )

            repost_queryset = Repost.objects.filter(user=self.user).order_by(
                "-timestamp"
            )
        else:
            say_queryset = Say.objects.filter(is_direct_mention=False).order_by(
                "-timestamp"
            )
            repost_queryset = Repost.objects.filter(user=self.user).order_by(
                "-timestamp"
            )

        # Merge and sort both querysets by the timestamp.
        merged_queryset = sorted(
            chain(say_queryset, repost_queryset),
            key=attrgetter("timestamp"),
            reverse=True,
        )

        return merged_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.user

        # Get all tags for this user's pins
        all_tags = []
        for say in Say.objects.filter(user=self.user):
            for tag in say.tags.all():
                all_tags.append(tag)

        for repost in Repost.objects.filter(user=self.user):
            for tag in repost.tags.all():
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
        context["no_citation_css"] = True

        return context


class SayDetailView(ShareDetailView):
    model = Say
    template_name = "write/say_detail.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.is_direct_mention and self.request.user not in obj.visible_to.all():
            raise Http404("You do not have permission to view this.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_voted"] = user_has_upvoted(self.request.user, self.object)
        return context


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


class SayUpdateView(LoginRequiredMixin, UpdateView):
    model = Say
    template_name = "write/say_update.html"
    form_class = SayForm

    def get_success_url(self):
        return reverse_lazy("write:say_detail", kwargs={"pk": self.object.id})


class SayDeleteView(LoginRequiredMixin, DeleteView):
    model = Say
    template_name = "write/say_confirm_delete.html"
    success_url = reverse_lazy("activity_feed:activity_feed")


class PinListView(ListView):
    model = Pin
    template_name = "write/pin_list.html"

    def dispatch(self, request, *args, **kwargs):
        # Get the User object
        self.user = get_object_or_404(
            get_user_model(), username=self.kwargs["username"]
        )

        # If the user's profile isn't public and the current user isn't authenticated, raise a 404 error
        if not self.user.is_public and not request.user.is_authenticated:
            return redirect("{}?next={}".format(reverse("login"), request.path))

        # Otherwise, proceed as normal
        return super().dispatch(request, *args, **kwargs)

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
        context["no_citation_css"] = True

        return context


class PinDetailView(ShareDetailView):
    model = Pin
    template_name = "write/pin_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_voted"] = user_has_upvoted(self.request.user, self.object)
        return context


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


class PinUpdateView(LoginRequiredMixin, UpdateView):
    model = Pin
    template_name = "write/pin_update.html"
    form_class = PinForm

    def get_success_url(self):
        return reverse_lazy("write:pin_detail", kwargs={"pk": self.object.id})


class PinDeleteView(LoginRequiredMixin, DeleteView):
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


class CommentUpdateView(LoginRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = "write/comment_update.html"

    def get_success_url(self):
        return self.object.content_object.get_absolute_url()


class CommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment
    template_name = "write/comment_confirm_delete.html"

    def get_success_url(self):
        return self.object.content_object.get_absolute_url()


class TagListView(ListView):
    template_name = "write/tag_list.html"

    def get_queryset(self):
        tag = self.kwargs["tag"]

        # Initialize querysets
        posts = Post.objects.filter(tags__name=tag)
        says = Say.objects.filter(tags__name=tag)
        pins = Pin.objects.filter(tags__name=tag)
        read_checkins = ReadCheckIn.objects.filter(tags__name=tag)
        watch_checkins = WatchCheckIn.objects.filter(tags__name=tag)
        listen_checkins = ListenCheckIn.objects.filter(tags__name=tag)
        game_checkins = GameCheckIn.objects.filter(tags__name=tag)
        reposts = Repost.objects.filter(tags__name=tag)

        # Combine all querysets into a single list and sort by timestamp
        combined_list = list(
            chain(
                posts,
                says,
                pins,
                read_checkins,
                watch_checkins,
                listen_checkins,
                game_checkins,
                reposts,
            )
        )
        sorted_list = sorted(combined_list, key=lambda x: x.timestamp, reverse=True)

        # Filter out items from non-public profiles if the user is not logged in
        if not self.request.user.is_authenticated:
            sorted_list = [item for item in sorted_list if item.user.is_public]

        # Add model names to each object
        for obj in sorted_list:
            obj.model_name = obj.__class__.__name__.lower()

        return sorted_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tag = self.kwargs["tag"]
        context["tag"] = tag
        context["users"] = User.objects.filter(
            bio__icontains=tag
        )  # these are the users with this tag in their bio

        # Get all tags from the sorted list
        all_tags = set()
        for obj in self.object_list:
            for t in obj.tags.all():
                all_tags.add(t)
        context["all_tags"] = all_tags

        return context


class TagUserListView(ListView):
    template_name = "write/tag_user_list.html"

    def dispatch(self, request, *args, **kwargs):
        # Get the User object
        self.user = get_object_or_404(
            get_user_model(), username=self.kwargs["username"]
        )

        # If the user's profile isn't public and the current user isn't authenticated, raise a 404 error
        if not self.user.is_public and not request.user.is_authenticated:
            return redirect("{}?next={}".format(reverse("login"), request.path))

        # Otherwise, proceed as normal
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        tag = self.kwargs["tag"]
        username = self.kwargs["username"]
        user = User.objects.get(username=username)

        posts = Post.objects.filter(tags__name=tag, user=user)
        says = Say.objects.filter(tags__name=tag, user=user)
        pins = Pin.objects.filter(tags__name=tag, user=user)
        reposts = Repost.objects.filter(tags__name=tag, user=user)
        read_checkins = ReadCheckIn.objects.filter(tags__name=tag, user=user)
        watch_checkins = WatchCheckIn.objects.filter(tags__name=tag, user=user)
        listen_checkins = ListenCheckIn.objects.filter(tags__name=tag, user=user)
        game_checkins = GameCheckIn.objects.filter(tags__name=tag, user=user)
        reposts = Repost.objects.filter(tags__name=tag, user=user)

        # Combine all querysets into a single list and sort by timestamp
        combined_list = list(
            chain(
                posts,
                says,
                pins,
                read_checkins,
                watch_checkins,
                listen_checkins,
                game_checkins,
                reposts,
            )
        )
        sorted_list = sorted(combined_list, key=lambda x: x.timestamp, reverse=True)

        # Add model names to each object
        for obj in sorted_list:
            obj.model_name = obj.__class__.__name__.lower()

        return sorted_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tag = self.kwargs["tag"]
        username = self.kwargs["username"]
        user = User.objects.get(username=username)

        context["tag"] = tag
        context["user"] = user  # the user whose tags we are viewing

        # Get all tags from the sorted list
        all_tags = set()
        for obj in self.object_list:
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
        # Check if the original activity is a repost and set original_repost accordingly
        if original_activity.content_type.model == "repost":
            repost.original_repost = original_activity.content_object
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_voted"] = user_has_upvoted(self.request.user, self.object)
        return context


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


class LuvListCreateView(CreateView):
    model = LuvList
    form_class = LuvListForm
    template_name = "write/luvlist_create.html"  # Assuming 'luvlist_form.html' is the template for the create view

    def get_context_data(self, **kwargs):
        data = super(LuvListCreateView, self).get_context_data(**kwargs)
        if self.request.POST:
            data["contents"] = ContentInListFormSet(self.request.POST)
        else:
            data["contents"] = ContentInListFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        contents = context["contents"]
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.save()
        if contents.is_valid():
            contents.instance = self.object
            contents.save()
        return super(LuvListCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse("write:luvlist_detail", args=[str(self.object.id)])


class LuvListDetailView(DetailView):
    model = LuvList
    template_name = "write/luvlist_detail.html"  # Assuming 'luvlist_detail.html' is the template for the detail view

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contents = self.object.contents.all()
        context["contents"] = contents

        # Get a random content from the LuvList
        context["random_content"] = random.choice(contents) if contents else None

        context["has_voted"] = user_has_upvoted(self.request.user, self.object)
        return context


class LuvListUpdateView(UpdateView):
    model = LuvList
    form_class = LuvListForm
    template_name = "write/luvlist_update.html"  # Assuming 'luvlist_form.html' is the template for the update view

    def get_context_data(self, **kwargs):
        data = super(LuvListUpdateView, self).get_context_data(**kwargs)
        if self.request.POST:
            data["contents"] = ContentInListFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["contents"] = ContentInListFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        contents = context["contents"]
        self.object = form.save()
        if contents.is_valid():
            contents.instance = self.object
            contents.save()
        return super(LuvListUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse("write:luvlist_detail", args=[str(self.object.id)])


class LuvListDeleteView(LoginRequiredMixin, DeleteView):
    model = LuvList
    template_name = "write/luvlist_delete.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        # Ensure only the owner can delete the LuvList
        return queryset.filter(user=self.request.user)

    def get_success_url(self):
        return reverse_lazy(
            "write:luvlist_list", args=[str(self.request.user.username)]
        )


class LuvListUserListView(ListView):
    model = LuvList
    template_name = "write/luvlist_list.html"  # Assuming 'luvlist_user_list.html' is the template for the user-specific list view

    def dispatch(self, request, *args, **kwargs):
        # Get the User object
        self.user = get_object_or_404(
            get_user_model(), username=self.kwargs["username"]
        )

        # If the user's profile isn't public and the current user isn't authenticated, raise a 404 error
        if not self.user.is_public and not request.user.is_authenticated:
            return redirect("{}?next={}".format(reverse("login"), request.path))

        # Otherwise, proceed as normal
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        self.user = get_object_or_404(
            get_user_model(), username=self.kwargs["username"]
        )
        return LuvList.objects.filter(user=self.user).order_by("-updated_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.user

        return context


def content_detail_redirect(request, content_id):
    content = get_object_or_404(ContentInList, id=content_id)

    # Based on the content type, redirect to the appropriate detail view
    if content.content_type.model == "luvlist":
        return redirect("write:luvlist_detail", content.content_object.id)
    elif content.content_type.model == "say":
        return redirect("write:say_detail", content.content_object.id)
    elif content.content_type.model == "pin":
        return redirect("write:pin_detail", content.content_object.id)
    elif content.content_type.model == "post":
        return redirect("write:post_detail", content.content_object.id)
    elif content.content_type.model == "book":
        return redirect("read:book_detail", content.content_object.id)
    elif content.content_type.model == "game":
        return redirect("play:game_detail", content.content_object.id)
    elif content.content_type.model == "movie":
        return redirect("watch:movie_detail", content.content_object.id)
    elif content.content_type.model == "series":
        return redirect("watch:series_detail", content.content_object.id)
    elif content.content_type.model == "release":
        return redirect("listen:release_detail", content.content_object.id)
    # Add more conditions if you have more content types
    else:
        return redirect(
            "write:luvlist_detail", content.luv_list.id
        )  # or redirect to some default


class RandomizerDetailView(DetailView):
    model = LuvList
    template_name = "write/luvlist_randomizer.html"
    context_object_name = "luv_list"

    def get_object(self):
        return get_object_or_404(LuvList, id=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        luv_list = self.get_object()

        user = self.request.user if self.request.user.is_authenticated else None

        randomizer = Randomizer.get_randomizer(luv_list, user)
        context["item"] = randomizer.generate_item()

        # Determine the timezone to use
        if user:
            user_tz = pytz.timezone(
                user.timezone
            )  # Make sure user.timezone is a valid timezone string
        else:
            user_tz = pytz.UTC  # Universal timezone for public randomizer

        # Calculate next midnight in the given timezone
        now = timezone.now()
        local_now = timezone.localtime(now, user_tz)
        next_midnight = local_now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        next_midnight_utc = next_midnight.astimezone(
            pytz.UTC
        )  # Directly use astimezone

        context["next_generated_datetime"] = next_midnight_utc

        # Calculate time until next renewal
        time_until_renewal = next_midnight_utc - now
        context["time_until_renewal"] = time_until_renewal

        return context


class CategoryAutocomplete(autocomplete.Select2QuerySetView):
    create_field = "name"  # This is the field used to create the new Category object

    def get_queryset(self):
        qs = Category.objects.filter(post__user=self.request.user).distinct()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs

    def create_object(self, text):
        return Category.objects.create(name=text)

    def has_add_permission(self, request):
        return True  # or customize this if you require special logic
