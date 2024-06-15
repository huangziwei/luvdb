import json
from datetime import timedelta
from itertools import chain
from operator import attrgetter

import pytz
import requests
from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, Q
from django.db.models.functions import Lower
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from django.views.generic.edit import FormMixin
from django_ratelimit.decorators import ratelimit

from activity_feed.models import Activity, Block
from discover.utils import user_has_upvoted
from listen.models import ListenCheckIn
from play.models import PlayCheckIn
from read.models import ReadCheckIn
from watch.models import WatchCheckIn
from write.utils_bluesky import create_bluesky_post
from write.utils_formatting import check_required_js
from write.utils_mastodon import create_mastodon_post

from .forms import (
    AlbumForm,
    CommentForm,
    ContentInListFormSet,
    LuvListForm,
    PhotoForm,
    PhotoNotesForm,
    PhotoUploadForm,
    PinForm,
    PostForm,
    RepostForm,
    SayForm,
)
from .models import (
    Album,
    Comment,
    ContentInList,
    LuvList,
    Photo,
    Pin,
    Post,
    Project,
    Randomizer,
    Repost,
    Say,
    Tag,
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
        context["repost_form"] = RepostForm(user=self.request.user)
        context["app_label"] = self.object._meta.app_label
        context["object_type"] = self.object._meta.model_name.lower()

        context["is_blocked"] = (
            Block.objects.filter(
                blocker=self.object.user, blocked=self.request.user
            ).exists()
            if self.request.user.is_authenticated
            else False
        )

        context["has_voted"] = user_has_upvoted(self.request.user, self.object)
        context["can_crosspost_mastodon"] = (
            self.request.user.is_authenticated
            and hasattr(self.request.user, "mastodon_account")
        )
        context["can_crosspost_bluesky"] = (
            self.request.user.is_authenticated
            and hasattr(self.request.user, "bluesky_account")
        )

        # Add the flags to the context
        include_mathjax, include_mermaid = check_required_js([self.object])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class PostListView(ListView):
    model = Post
    template_name = "write/post_list.html"
    paginate_by = 100

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

        if "project" in self.kwargs:
            project = Project.objects.filter(
                slug=self.kwargs["project"], post__user=self.user
            ).first()
            if project:
                queryset = queryset.filter(projects=project)
                if project.order == Project.NEWEST_FIRST:
                    queryset = queryset.order_by("-timestamp")
                elif project.order == Project.OLDEST_FIRST:
                    queryset = queryset.order_by("timestamp")
                elif project.order == Project.BY_TITLE:
                    queryset = queryset.order_by("title")
            else:
                queryset = Post.objects.none()
        else:
            queryset = queryset.filter(projects__isnull=True).order_by("-timestamp")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.user

        # Determine current project, if any
        current_project_slug = self.kwargs.get("project", None)
        current_project = Project.objects.filter(slug=current_project_slug).first()

        # Filter tags based on the selected project
        if current_project:
            all_tags = (
                Tag.objects.filter(post__user=self.user, post__projects=current_project)
                .annotate(count=Count("post"))
                .order_by(Lower("name"))
            )
        else:
            all_tags = (
                Tag.objects.filter(post__user=self.user, post__projects__isnull=True)
                .annotate(count=Count("post"))
                .order_by(Lower("name"))
            )

        context["all_tags"] = all_tags
        # Add posts count to projects
        projects_with_counts = []
        for project in (
            Project.objects.filter(post__user=self.user).distinct().order_by("name")
        ):
            post_count = Post.objects.filter(user=self.user, projects=project).count()
            projects_with_counts.append({"project": project, "post_count": post_count})

        context["all_projects"] = projects_with_counts

        if current_project:
            context["current_project"] = {
                "name": current_project.name,
                "slug": current_project.slug,
            }
        else:
            context["current_project"] = None

        context["is_blocked"] = (
            Block.objects.filter(blocker=self.user, blocked=self.request.user).exists()
            if self.request.user.is_authenticated
            else False
        )

        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class PostDetailView(ShareDetailView):
    model = Post
    template_name = "write/post_detail.html"

    def post(self, request, *args, **kwargs):
        luvpost = self.get_object()
        if "crosspost_mastodon" in request.POST and hasattr(
            request.user, "mastodon_account"
        ):
            url = request.build_absolute_uri(luvpost.get_absolute_url())
            create_mastodon_post(
                handle=request.user.mastodon_account.mastodon_handle,
                access_token=request.user.mastodon_account.get_mastodon_access_token(),
                text=luvpost.title,
                url=url,
            )
        elif "crosspost_bluesky" in request.POST and hasattr(
            request.user, "bluesky_account"
        ):
            url = request.build_absolute_uri(luvpost.get_absolute_url())
            create_bluesky_post(
                handle=request.user.bluesky_account.bluesky_handle,
                pds_url=request.user.bluesky_account.bluesky_pds_url,
                password=request.user.bluesky_account.get_bluesky_app_password(),
                text=luvpost.title,
                content_id=luvpost.id,
                content_username=request.user.username,
                content_type="Post",
            )
        return HttpResponseRedirect(request.path_info)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["projects"] = self.object.projects.all()

        # New code to order posts within projects
        projects_with_ordered_posts = []
        for project in self.object.projects.all():
            # Fetch the posts for the project
            posts = project.post_set.all()

            # Order the posts based on the project's order setting
            if project.order == Project.NEWEST_FIRST:
                ordered_posts = posts.order_by("-timestamp")
            elif project.order == Project.OLDEST_FIRST:
                ordered_posts = posts.order_by("timestamp")
            elif project.order == Project.BY_TITLE:
                ordered_posts = posts.order_by("title")
            else:
                # Default ordering if needed
                ordered_posts = posts

            # Add the project along with its ordered posts to the list
            projects_with_ordered_posts.append((project, ordered_posts))

        # Add the list to the context
        context["projects_with_ordered_posts"] = projects_with_ordered_posts

        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = "write/post_create.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "write:post_detail_slug",
            kwargs={"slug": self.object.slug, "username": self.object.user.username},
        )


class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    template_name = "write/post_update.html"
    form_class = PostForm

    def get_success_url(self):
        return reverse_lazy(
            "write:post_detail_slug",
            kwargs={"slug": self.object.slug, "username": self.object.user.username},
        )


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = "write/post_confirm_delete.html"
    success_url = reverse_lazy("activity_feed:activity_feed")


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    template_name = "write/project_update.html"
    fields = ["name", "order"]
    slug_url_kwarg = "project"


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class SayListView(ListView):
    model = Say
    template_name = "write/say_list.html"
    paginate_by = 25

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
        context["user"] = user = self.user

        # Aggregating tag counts from Say
        say_tags = (
            Tag.objects.filter(say__user=self.user)
            .values("name")
            .annotate(count=Count("say"))
        )

        # Aggregating tag counts from Repost
        repost_tags = (
            Tag.objects.filter(repost__user=self.user)
            .values("name")
            .annotate(count=Count("repost"))
        )

        # Combining the tag counts
        combined_tags = {tag["name"]: tag["count"] for tag in say_tags}
        for tag in repost_tags:
            combined_tags[tag["name"]] = (
                combined_tags.get(tag["name"], 0) + tag["count"]
            )

        # Converting combined tags to the desired format
        sorted_combined_tags = [
            {"name": name, "count": count}
            for name, count in sorted(
                combined_tags.items(), key=lambda item: item[0].lower()
            )
        ]

        context["all_tags"] = sorted_combined_tags
        context["no_citation_css"] = True

        include_mathjax, include_mermaid = check_required_js(context["page_obj"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        context["is_blocked"] = (
            Block.objects.filter(blocker=user, blocked=self.request.user).exists()
            if self.request.user.is_authenticated
            else False
        )

        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class SayDetailView(ShareDetailView):
    model = Say
    template_name = "write/say_detail.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.is_direct_mention and self.request.user not in obj.visible_to.all():
            raise Http404("You do not have permission to view this.")
        return obj

    def post(self, request, *args, **kwargs):
        say = self.get_object()
        if "crosspost_mastodon" in request.POST and hasattr(
            request.user, "mastodon_account"
        ):
            url = request.build_absolute_uri(say.get_absolute_url())
            create_mastodon_post(
                handle=request.user.mastodon_account.mastodon_handle,
                access_token=request.user.mastodon_account.get_mastodon_access_token(),
                text=say.content,
                url=url,
            )
        elif "crosspost_bluesky" in request.POST and hasattr(
            request.user, "bluesky_account"
        ):
            url = request.build_absolute_uri(say.get_absolute_url())
            create_bluesky_post(
                handle=request.user.bluesky_account.bluesky_handle,
                pds_url=request.user.bluesky_account.bluesky_pds_url,
                password=request.user.bluesky_account.get_bluesky_app_password(),
                text=say.content,
                content_id=say.id,
                content_username=request.user.username,
                content_type="Say",
            )
        return HttpResponseRedirect(request.path_info)


class SayCreateView(LoginRequiredMixin, CreateView):
    model = Say
    form_class = SayForm
    # fields = ["content"]
    template_name = "write/say_create.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "write:say_detail",
            kwargs={"pk": self.object.id, "username": self.object.user.username},
        )


class SayUpdateView(LoginRequiredMixin, UpdateView):
    model = Say
    template_name = "write/say_update.html"
    form_class = SayForm

    def get_success_url(self):
        return reverse_lazy(
            "write:say_detail",
            kwargs={"pk": self.object.id, "username": self.object.user.username},
        )


class SayDeleteView(LoginRequiredMixin, DeleteView):
    model = Say
    template_name = "write/say_confirm_delete.html"
    success_url = reverse_lazy("activity_feed:activity_feed")


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class PinListView(ListView):
    model = Pin
    template_name = "write/pin_list.html"
    paginate_by = 25

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
        queryset = Pin.objects.filter(user=self.user)
        if "project" in self.kwargs:
            project = Project.objects.filter(
                slug=self.kwargs["project"], pin__user=self.user
            ).first()
            if project:
                queryset = queryset.filter(projects=project)
                if project.order == Project.NEWEST_FIRST:
                    queryset = queryset.order_by("-timestamp")
                elif project.order == Project.OLDEST_FIRST:
                    queryset = queryset.order_by("timestamp")
                elif project.order == Project.BY_TITLE:
                    queryset = queryset.order_by("title")
            else:
                queryset = Post.objects.none()
        else:
            queryset = queryset.filter(projects__isnull=True).order_by("-timestamp")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.user

        # Determine current project, if any
        current_project_slug = self.kwargs.get("project", None)
        current_project = Project.objects.filter(slug=current_project_slug).first()

        # Filter tags based on the selected project
        if current_project:
            all_tags = (
                Tag.objects.filter(pin__user=self.user, pin__projects=current_project)
                .annotate(count=Count("pin"))
                .order_by(Lower("name"))
            )
        else:
            all_tags = (
                Tag.objects.filter(pin__user=self.user, pin__projects__isnull=True)
                .annotate(count=Count("pin"))
                .order_by(Lower("name"))
            )

        context["all_tags"] = all_tags
        context["no_citation_css"] = True

        # Add the flags to the context
        include_mathjax, include_mermaid = check_required_js(context["page_obj"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        context["is_blocked"] = (
            Block.objects.filter(blocker=self.user, blocked=self.request.user).exists()
            if self.request.user.is_authenticated
            else False
        )

        current_project_slug = self.kwargs.get("project", None)
        current_project_obj = Project.objects.filter(slug=current_project_slug).first()

        if current_project:
            context["current_project"] = {
                "name": current_project.name,
                "slug": current_project.slug,
            }
        else:
            context["current_project"] = None

        projects_with_counts = []
        for project in (
            Project.objects.filter(pin__user=self.user).distinct().order_by("name")
        ):
            post_count = Pin.objects.filter(user=self.user, projects=project).count()
            projects_with_counts.append({"project": project, "post_count": post_count})

        context["all_projects"] = projects_with_counts

        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class PinDetailView(ShareDetailView):
    model = Pin
    template_name = "write/pin_detail.html"

    def post(self, request, *args, **kwargs):
        pin = self.get_object()
        if "crosspost_mastodon" in request.POST and hasattr(
            request.user, "mastodon_account"
        ):
            url = pin.url
            create_mastodon_post(
                handle=request.user.mastodon_account.mastodon_handle,
                access_token=request.user.mastodon_account.get_mastodon_access_token(),
                text=pin.title + "\n\n" + "> " + pin.content,
                url=url,
            )
        elif "crosspost_bluesky" in request.POST and hasattr(
            request.user, "bluesky_account"
        ):
            url = pin.url
            create_bluesky_post(
                handle=request.user.bluesky_account.bluesky_handle,
                pds_url=request.user.bluesky_account.bluesky_pds_url,
                password=request.user.bluesky_account.get_bluesky_app_password(),
                text=pin.title + "\n\n" + "> " + pin.content,
                content_id=pin.id,
                content_username=request.user.username,
                content_type="Pin",
            )
        return HttpResponseRedirect(request.path_info)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["projects"] = self.object.projects.all()
        return context


class PinCreateView(LoginRequiredMixin, CreateView):
    model = Pin
    form_class = PinForm
    template_name = "write/pin_create.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

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
        return reverse(
            "write:pin_detail",
            kwargs={"pk": self.object.id, "username": self.object.user.username},
        )


class PinUpdateView(LoginRequiredMixin, UpdateView):
    model = Pin
    template_name = "write/pin_update.html"
    form_class = PinForm

    def get_success_url(self):
        return reverse_lazy(
            "write:pin_detail",
            kwargs={"pk": self.object.id, "username": self.object.user.username},
        )


class PinDeleteView(LoginRequiredMixin, DeleteView):
    model = Pin
    template_name = "write/pin_confirm_delete.html"
    success_url = reverse_lazy("activity_feed:activity_feed")


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class PinsFromURLView(ListView):
    model = Pin
    template_name = "write/pins_from_url.html"
    context_object_name = "pins"
    paginate_by = 25

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

        # Add the flags to the context
        include_mathjax, include_mermaid = check_required_js(context["page_obj"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid
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


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class TagListView(ListView):
    template_name = "write/tag_list.html"
    paginate_by = 25

    def get_queryset(self):
        tag = self.kwargs["tag"]

        # Initialize querysets
        posts = Post.objects.filter(tags__name=tag)
        says = Say.objects.filter(tags__name=tag)
        pins = Pin.objects.filter(tags__name=tag)
        luvlists = LuvList.objects.filter(tags__name=tag)
        read_checkins = ReadCheckIn.objects.filter(tags__name=tag)
        watch_checkins = WatchCheckIn.objects.filter(tags__name=tag)
        listen_checkins = ListenCheckIn.objects.filter(tags__name=tag)
        play_checkins = PlayCheckIn.objects.filter(tags__name=tag)
        reposts = Repost.objects.filter(tags__name=tag)

        # Combine all querysets into a single list and sort by timestamp
        combined_list = list(
            chain(
                posts,
                says,
                pins,
                luvlists,
                read_checkins,
                watch_checkins,
                listen_checkins,
                play_checkins,
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

        # Aggregate tag counts from various models
        models = [
            Post,
            Say,
            Pin,
            LuvList,
            ReadCheckIn,
            WatchCheckIn,
            ListenCheckIn,
            PlayCheckIn,
            Repost,
        ]
        tag_counts = {}

        for model in models:
            model_name = model.__name__.lower()
            tags = (
                Tag.objects.filter(**{model_name + "__tags__name": tag})
                .values("name")
                .annotate(count=Count(model_name))
            )
            for t in tags:
                tag_counts[t["name"]] = tag_counts.get(t["name"], 0) + t["count"]

        # Sorting tags alphabetically
        sorted_tags = sorted(
            [{"name": name, "count": count} for name, count in tag_counts.items()],
            key=lambda x: x["name"].lower(),
        )
        context["all_tags"] = sorted_tags

        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class TagUserListView(ListView):
    template_name = "write/tag_user_list.html"
    paginate_by = 25

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
        luvlists = LuvList.objects.filter(tags__name=tag, user=user)
        reposts = Repost.objects.filter(tags__name=tag, user=user)
        read_checkins = ReadCheckIn.objects.filter(tags__name=tag, user=user)
        watch_checkins = WatchCheckIn.objects.filter(tags__name=tag, user=user)
        listen_checkins = ListenCheckIn.objects.filter(tags__name=tag, user=user)
        play_checkins = PlayCheckIn.objects.filter(tags__name=tag, user=user)
        reposts = Repost.objects.filter(tags__name=tag, user=user)

        # Combine all querysets into a single list and sort by timestamp
        combined_list = list(
            chain(
                posts,
                says,
                pins,
                luvlists,
                read_checkins,
                watch_checkins,
                listen_checkins,
                play_checkins,
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

        # Aggregate tag counts from various models for the specific user
        models = [
            Post,
            Say,
            Pin,
            LuvList,
            ReadCheckIn,
            WatchCheckIn,
            ListenCheckIn,
            PlayCheckIn,
            Repost,
        ]
        tag_counts = {}

        for model in models:
            model_name = model.__name__.lower()
            tags = (
                Tag.objects.filter(
                    **{model_name + "__tags__name": tag, model_name + "__user": user}
                )
                .values("name")
                .annotate(count=Count(model_name))
            )
            for t in tags:
                tag_counts[t["name"]] = tag_counts.get(t["name"], 0) + t["count"]

        # Sorting tags alphabetically
        sorted_tags = sorted(
            [{"name": name, "count": count} for name, count in tag_counts.items()],
            key=lambda x: x["name"].lower(),
        )

        context["all_tags"] = sorted_tags

        context["is_blocked"] = (
            Block.objects.filter(blocker=user, blocked=self.request.user).exists()
            if self.request.user.is_authenticated
            else False
        )

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


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class RepostDetailView(ShareDetailView):
    model = Repost
    template_name = "write/repost_detail.html"
    context_object_name = "repost"

    def post(self, request, *args, **kwargs):
        repost = self.get_object()
        if "crosspost_mastodon" in request.POST and hasattr(
            request.user, "mastodon_account"
        ):
            url = request.build_absolute_uri(repost.get_absolute_url())
            create_mastodon_post(
                handle=request.user.mastodon_account.mastodon_handle,
                access_token=request.user.mastodon_account.get_mastodon_access_token(),
                text=repost.content,
                url=url,
            )
        elif "crosspost_bluesky" in request.POST and hasattr(
            request.user, "bluesky_account"
        ):
            url = request.build_absolute_uri(repost.get_absolute_url())
            create_bluesky_post(
                handle=request.user.bluesky_account.bluesky_handle,
                pds_url=request.user.bluesky_account.bluesky_pds_url,
                password=request.user.bluesky_account.get_bluesky_app_password(),
                text=repost.content,
                content_id=repost.id,
                content_username=request.user.username,
                content_type="Repost",
            )
        return HttpResponseRedirect(request.path_info)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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


class LuvListCreateView(LoginRequiredMixin, CreateView):
    model = LuvList
    form_class = LuvListForm
    template_name = "write/luvlist_create.html"  # Assuming 'luvlist_form.html' is the template for the create view

    def form_valid(self, form):
        context = self.get_context_data()
        contents = context["contents"]
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.save()
        self.object.collaborators.add(self.request.user)
        if contents.is_valid():
            contents.instance = self.object
            contents.save()
        return super(LuvListCreateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        data = super(LuvListCreateView, self).get_context_data(**kwargs)
        if self.request.POST:
            data["contents"] = ContentInListFormSet(self.request.POST)
        else:
            data["contents"] = ContentInListFormSet()
        return data

    def get_success_url(self):
        return reverse(
            "write:luvlist_detail",
            kwargs={"pk": self.object.id, "username": self.object.user.username},
        )


@method_decorator(ratelimit(key="ip", rate="20/m", block=True), name="dispatch")
class LuvListDetailView(DetailView):
    model = LuvList
    template_name = "write/luvlist_detail.html"

    def get_paginate_by(self, queryset):
        """
        Get the number of items to paginate by, according to the user's preference.
        """
        return self.object.items_per_page  # Default is 10 if not set

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        visitor_order_preference = request.POST.get("order")
        session_key = f"order_{self.object.id}"  # Unique key for each list
        if visitor_order_preference in ["ASC", "DESC"]:
            request.session[session_key] = visitor_order_preference
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get("search", "")

        # Optimize content fetching
        order = self.request.session.get(
            f"order_{self.object.id}", self.object.order_preference
        )
        order_by_field = "order" if order == "ASC" else "-order"
        contents_queryset = self.object.contents.all()
        if search_query:
            contents_queryset = self.filter_contents(contents_queryset, search_query)

        context["order"] = order
        context["contents"] = contents_queryset.order_by(order_by_field)
        context["collaborators"] = self.object.collaborators.all().order_by("username")

        # statistics
        content_counts = (
            self.object.contents.values("content_type__model")
            .annotate(total=Count("content_type"))
            .order_by()
        )
        content_count_dict = {
            count["content_type__model"]: count["total"] for count in content_counts
        }

        # Update context with the counts
        context.update(
            {
                "book_count": content_count_dict.get("book", 0),
                "movie_count": content_count_dict.get("movie", 0),
                "series_count": content_count_dict.get("series", 0),
                "release_count": content_count_dict.get("release", 0),
                "audiobook_count": content_count_dict.get("audiobook", 0),
                "podcast_count": content_count_dict.get("podcast", 0),
                "game_count": content_count_dict.get("game", 0),
            }
        )

        context["is_blocked"] = (
            Block.objects.filter(
                blocker=self.object.user, blocked=self.request.user
            ).exists()
            if self.request.user.is_authenticated
            else False
        )

        paginate_by = self.get_paginate_by(context["contents"])
        if paginate_by is not None:
            # Pagination logic
            page = self.request.GET.get("page")
            paginator = Paginator(context["contents"], paginate_by)
            context["page_ranges"] = self.get_page_ranges(paginator, paginate_by, order)

            try:
                context["contents"] = paginator.page(page)
            except PageNotAnInteger:
                context["contents"] = paginator.page(1)
            except EmptyPage:
                context["contents"] = paginator.page(paginator.num_pages)

        return context

    def get_page_ranges(self, paginator, items_per_page, order):
        page_ranges = []
        total_pages = paginator.num_pages
        total_items = paginator.count

        for i in range(1, total_pages + 1):
            if order == "ASC":
                start = (i - 1) * items_per_page + 1
                end = start + items_per_page - 1
                if end > total_items:
                    end = total_items
                page_ranges.append((i, f"{start}-{end}"))
            else:  # order == "DSC"
                end = total_items - (i - 1) * items_per_page
                start = end - items_per_page + 1
                if start < 1:
                    start = 1
                page_ranges.append((i, f"{end}-{start}"))

        if order == "DSC":
            page_ranges.reverse()

        return page_ranges

    def filter_contents(self, queryset, keyword):
        filtered_queryset = queryset
        valid_contents = []
        content_role_map = {
            "Release": "ReleaseRole",
            "Book": "BookRole",
            "Movie": "MovieRole",
            "Series": "SeriesRole",
            "Game": "GameRole",
        }
        for content in queryset:
            try:
                # Check if the content_object has a title field and match the keyword
                has_title = False
                if hasattr(content.content_object, "title"):
                    if keyword.lower() in content.content_object.title.lower():
                        has_title = True

                # Check for creators dynamically based on content_object type
                has_creator = False
                content_type = type(content.content_object).__name__
                role_model = content_role_map.get(content_type, None)

                if role_model and hasattr(content.content_object, "creators"):
                    # Access the through model dynamically
                    creators = (
                        getattr(content.content_object, "creators")
                        .through.objects.filter(
                            **{content_type.lower(): content.content_object}
                        )
                        .select_related("creator")
                    )

                    for role in creators:
                        if keyword.lower() in role.creator.name.lower():
                            has_creator = True

                # Add content to valid_contents if either title or creator matches
                if has_title or has_creator:
                    valid_contents.append(content.id)

            except Exception as e:
                # Handle exceptions, potentially log or further investigate these
                continue

        return filtered_queryset.filter(id__in=valid_contents)

    def get_success_url(self):
        return reverse(
            "write:luvlist_detail",
            kwargs={"pk": self.object.id, "username": self.object.user.username},
        )


class LuvListUpdateView(LoginRequiredMixin, UpdateView):
    model = LuvList
    form_class = LuvListForm
    template_name = "write/luvlist_update.html"  # Assuming 'luvlist_form.html' is the template for the update view

    def get_page_ranges(self, paginator, items_per_page, order):
        page_ranges = []
        total_pages = paginator.num_pages
        total_items = paginator.count

        for i in range(1, total_pages + 1):
            if order == "ASC":
                start = (i - 1) * items_per_page + 1
                end = start + items_per_page - 1
                if end > total_items:
                    end = total_items
                page_ranges.append((i, f"{start}-{end}"))
            else:  # "DSC"
                end = total_items - (i - 1) * items_per_page
                start = end - items_per_page + 1
                if start < 1:
                    start = 1
                page_ranges.append((i, f"{end}-{start}"))

        if order == "DSC":
            page_ranges.reverse()

        return page_ranges

    def get_context_data(self, **kwargs):
        data = super(LuvListUpdateView, self).get_context_data(**kwargs)
        items_per_page = self.object.items_per_page  # Set the number of items per page

        # Get all content items related to the LuvList instance
        order_preference = self.object.order_preference
        order_by_field = "order" if order_preference == "ASC" else "-order"

        all_contents = ContentInList.objects.filter(luv_list=self.object).order_by(
            order_by_field
        )

        # Setting up pagination
        paginator = Paginator(all_contents, items_per_page)
        page_number = self.request.GET.get("page") or 1
        page_obj = paginator.get_page(page_number)

        if self.request.POST:
            data["contents"] = ContentInListFormSet(
                self.request.POST,
                queryset=page_obj.object_list,  # Load only the current page items
                instance=self.object,
            )
        else:
            data["contents"] = ContentInListFormSet(
                queryset=page_obj.object_list,  # Load only the current page items
                instance=self.object,
            )

        data["page_obj"] = page_obj  # Add page object to context to use in template
        data["page_ranges"] = self.get_page_ranges(
            paginator, items_per_page, self.object.order_preference
        )  # Adjust "ASC" as needed
        return data

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        context = self.get_context_data()
        contents = context["contents"]
        self.object = form.save()
        if self.object.allow_collaboration:
            self.object.collaborators.add(self.request.user)
        if contents.is_valid():
            contents.instance = self.object
            contents.save()
        return super(LuvListUpdateView, self).form_valid(form)

    def get_success_url(self):
        if self.object.allow_collaboration:
            # Redirect to the collaboration URL if collaboration is allowed
            return reverse("write:luvlist_detail_collab", kwargs={"pk": self.object.id})
        else:
            # Redirect to the regular URL if collaboration is not allowed
            return reverse(
                "write:luvlist_detail",
                kwargs={"pk": self.object.id, "username": self.object.user.username},
            )


class LuvListDeleteView(LoginRequiredMixin, DeleteView):
    model = LuvList
    template_name = "write/luvlist_delete.html"

    def dispatch(self, request, *args, **kwargs):
        # Get the current LuvList object
        luvlist = get_object_or_404(LuvList, pk=kwargs["pk"])

        # Check if the current user is the creator of the LuvList
        if luvlist.user != request.user:
            # Return a forbidden response
            return HttpResponseForbidden(
                "You are not authorized to delete this LuvList."
            )

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        # Ensure only the owner can delete the LuvList
        return queryset.filter(user=self.request.user)

    def get_success_url(self):
        return reverse_lazy(
            "write:luvlist_list", args=[str(self.request.user.username)]
        )


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
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
        context["user"] = self.user

        # Aggregating tag counts from LuvList
        all_tags = (
            Tag.objects.filter(luvlist__user=self.user)
            .values("name")
            .annotate(count=Count("luvlist"))
            .order_by(Lower("name"))
        )
        context["all_tags"] = all_tags

        # Add collaborated luvlists to the context
        collaborated_luvlists = (
            LuvList.objects.filter(collaborators=self.user)
            .exclude(user=self.user)
            .distinct()
        )
        context["collaborated_luvlists"] = collaborated_luvlists

        context["is_blocked"] = (
            Block.objects.filter(blocker=self.user, blocked=self.request.user).exists()
            if self.request.user.is_authenticated
            else False
        )

        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
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

    def post(self, request, *args, **kwargs):
        if "restart_order" in request.POST:
            luv_list = self.get_object()
            user = request.user if request.user.is_authenticated else None
            randomizer = Randomizer.get_randomizer(luv_list, user)
            randomizer.restart_random_order()  # Restart the randomized order

        return self.get(
            request, *args, **kwargs
        )  # Redirect to the same page to display the updated order


class ProjectAutocomplete(autocomplete.Select2QuerySetView):
    create_field = "name"  # This is the field used to create the new Project object

    def get_queryset(self):
        form_type = self.kwargs.get("form_type")
        if form_type == "post":
            qs = Project.objects.filter(post__user=self.request.user).distinct()
        elif form_type == "pin":
            qs = Project.objects.filter(pin__user=self.request.user).distinct()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs

    def create_object(self, text):
        return Project.objects.create(name=text)

    def has_add_permission(self, request):
        return True  # or customize this if you require special logic


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class CommentListView(ListView):
    model = Comment
    template_name = "write/comment_list.html"
    paginate_by = 25

    def get_queryset(self):
        """
        Return the list of items for this view.
        The queryset consists of comments made by the currently logged-in user.
        """
        return Comment.objects.filter(user=self.request.user).order_by("-timestamp")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.request.user
        return context


def surprise_manifest(request, luvlist_id, username=None):
    luvlist = LuvList.objects.get(id=luvlist_id)
    data = {
        "short_name": luvlist.short_name if luvlist.short_name else "Surprise",
        "name": luvlist.title,
        "scope": "/luvlist/",
        "display": "standalone",
        "icons": [
            {
                "src": "https://img-luvdb.s3.amazonaws.com/static/img/android-chrome-192x192.png",
                "sizes": "192x192",
                "type": "image/png",
            },
            {
                "src": "https://img-luvdb.s3.amazonaws.com/static/img/android-chrome-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
            },
        ],
        "theme_color": "#ffffff",
        "background_color": "#ffffff",
    }
    return HttpResponse(json.dumps(data), content_type="application/json")


# Album and Photo
class AlbumDetailView(FormMixin, ShareDetailView):
    model = Album
    template_name = "write/album_detail.html"
    context_object_name = "album"
    form_class = PhotoUploadForm
    paginate_by = 9  # Number of photos per page

    def get_success_url(self):
        return self.request.path

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        photo = form.save(commit=False)
        photo.album = self.get_object()
        photo.user = self.request.user
        photo.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        album = self.get_object()
        photos = album.photos.all()
        paginator = Paginator(photos, self.paginate_by)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        context["page_obj"] = page_obj
        return context


class AlbumCreateView(CreateView):
    model = Album
    form_class = AlbumForm
    template_name = "write/album_create.html"
    paginate_by = 9

    def form_valid(self, form):
        form.instance.user = (
            self.request.user
        )  # Set the user to the current logged in user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "write:album_detail",
            kwargs={"pk": self.object.id, "username": self.object.user.username},
        )


class AlbumUpdateView(UpdateView):
    model = Album
    form_class = AlbumForm
    template_name = "write/album_update.html"

    def get_queryset(self):
        # Ensure that only the owner can update their album
        return self.model.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse(
            "write:album_detail",
            kwargs={"pk": self.object.id, "username": self.object.user.username},
        )


class AlbumDeleteView(DeleteView):
    model = Album
    template_name = "write/album_confirm_delete.html"
    success_url = reverse_lazy("write:album_list")

    def get_queryset(self):
        # Ensure that only the owner can delete their album
        return self.model.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse(
            "write:album_list", kwargs={"username": self.request.user.username}
        )


class AlbumListView(ListView):
    model = Album
    template_name = "write/album_list.html"
    context_object_name = "albums"

    def get_queryset(self):
        self.user = get_object_or_404(User, username=self.kwargs["username"])
        return Album.objects.filter(user=self.user).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.user
        return context


class PhotoDetailView(ShareDetailView):
    model = Photo
    template_name = "write/photo_detail.html"
    context_object_name = "photo"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["album"] = self.object.album

        photo = self.get_object()
        album_photos = list(photo.album.photos.all())
        photo_index = album_photos.index(photo)

        if photo_index > 0:
            context["previous_photo"] = album_photos[photo_index - 1]
        else:
            context["previous_photo"] = None

        if photo_index < len(album_photos) - 1:
            context["next_photo"] = album_photos[photo_index + 1]
        else:
            context["next_photo"] = None

        context["photo_index"] = photo_index + 1
        context["photo_count"] = len(album_photos)

        if not photo.notes:
            context["notes_form"] = PhotoNotesForm(instance=photo)

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = PhotoNotesForm(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            return redirect(self.request.path)
        return self.get(request, *args, **kwargs)


class PhotoUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Photo
    form_class = PhotoForm
    template_name = "write/photo_update.html"
    context_object_name = "photo"

    def test_func(self):
        photo = self.get_object()
        return self.request.user == photo.user

    def get_success_url(self):
        return reverse_lazy(
            "write:photo_detail",
            kwargs={"pk": self.object.pk, "username": self.object.user.username},
        )


class PhotoDeleteView(LoginRequiredMixin, DeleteView):
    model = Photo
    template_name = "write/photo_confirm_delete.html"

    def get_queryset(self):
        # Ensure that only the owner can delete their photo
        return self.model.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse(
            "write:album_detail",
            kwargs={"pk": self.object.album.id, "username": self.object.user.username},
        )
