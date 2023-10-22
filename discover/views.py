from datetime import timedelta
from itertools import chain
from random import sample

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Case, Count, F, IntegerField, Q, Sum, Value, When
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import ListView

from listen.models import ListenCheckIn
from play.models import GameCheckIn
from read.models import ReadCheckIn
from watch.models import WatchCheckIn
from write.models import LuvList, Pin, Post, Repost, Say

from .models import Vote

User = get_user_model()

###########
# helpers #
###########


def user_has_upvoted(user, obj):
    if not user.is_authenticated:
        return False

    content_type = ContentType.objects.get_for_model(obj)
    return Vote.objects.filter(
        user=user,
        content_type=content_type,
        object_id=obj.id,
        value=Vote.UPVOTE,
    ).exists()


#########
# views #
#########


@login_required
def vote(request, content_type, object_id, vote_type):
    model_class = ContentType.objects.get(model=content_type).model_class()
    obj = get_object_or_404(model_class, id=object_id)

    # Prevent users from voting on their own content
    # if hasattr(obj, "user") and obj.user == request.user:
    #     return HttpResponseForbidden(
    #         "Nice try! But no, you cannot vote on your own content."
    #     )

    content_type = ContentType.objects.get_for_model(obj)
    existing_vote = Vote.objects.filter(
        content_type=content_type, object_id=obj.id, user=request.user
    ).first()

    if vote_type == "up":
        if existing_vote:
            if existing_vote.value == Vote.UPVOTE:
                existing_vote.delete()
            else:
                existing_vote.value = Vote.UPVOTE
                existing_vote.save()
        else:
            Vote.objects.create(
                content_type=content_type,
                object_id=obj.id,
                user=request.user,
                value=Vote.UPVOTE,
            )
    # elif vote_type == "down":
    #     if existing_vote:
    #         if existing_vote.value == Vote.DOWNVOTE:
    #             existing_vote.delete()
    #         else:
    #             existing_vote.value = Vote.DOWNVOTE
    #             existing_vote.save()
    #     else:
    #         Vote.objects.create(
    #             content_type=content_type,
    #             object_id=obj.id,
    #             user=request.user,
    #             value=Vote.DOWNVOTE,
    #         )

    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


class DiscoverListAllView(ListView):
    template_name = "discover/discover_all.html"

    def get_queryset(self):
        return None  # We override `get_context_data` to send multiple querysets

    def annotate_vote_count(self, model, time_condition=None):
        if time_condition is None:
            return model.objects.annotate(
                vote_count=Sum(
                    Case(
                        When(Q(votes__value__isnull=False), then=F("votes__value")),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                )
            )
        else:
            condition = Q(**time_condition)
            return model.objects.annotate(
                vote_count=Sum(
                    Case(
                        When(condition, then=F("votes__value")),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                )
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_by = self.request.GET.get("order_by", "random")  # Default to 'random'

        models_list = [
            (Post, "posts"),
            (Pin, "pins"),
            (LuvList, "lists"),
            (ReadCheckIn, "read_checkins"),
            (WatchCheckIn, "watch_checkins"),
            (ListenCheckIn, "listen_checkins"),
            (GameCheckIn, "game_checkins"),
        ]

        if order_by == "trending":
            seven_days_ago = timezone.now() - timedelta(days=7)
            time_condition = {"votes__timestamp__gte": seven_days_ago}
            say_and_reposts = list(
                chain(
                    self.annotate_vote_count(Say, time_condition).filter(
                        vote_count__gt=-1
                    ),
                    self.annotate_vote_count(Repost, time_condition).filter(
                        vote_count__gt=-1
                    ),
                )
            )
            say_and_reposts = sorted(
                say_and_reposts, key=lambda x: (x.vote_count, x.timestamp), reverse=True
            )
            context["says_and_reposts"] = say_and_reposts[:10]

            for model, model_name in models_list:
                context[model_name] = (
                    self.annotate_vote_count(model, time_condition)
                    .filter(vote_count__gt=-1)
                    .order_by("-vote_count", "-timestamp")
                )[:10]

        elif order_by == "all_time":
            time_condition = None
            say_and_reposts = list(
                chain(
                    self.annotate_vote_count(Say, time_condition),
                    self.annotate_vote_count(Repost, time_condition),
                )
            )
            say_and_reposts = sorted(
                say_and_reposts, key=lambda x: (x.vote_count, x.timestamp), reverse=True
            )
            context["says_and_reposts"] = say_and_reposts[:10]

            for model, model_name in models_list:
                context[model_name] = (
                    self.annotate_vote_count(model, time_condition).order_by(
                        "-vote_count", "-timestamp"
                    )
                )[:10]

        elif order_by == "newest":
            say_and_reposts = list(
                chain(
                    Say.objects.all().order_by("-timestamp"),
                    Repost.objects.all().order_by("-timestamp"),
                )
            )
            say_and_reposts.sort(key=lambda x: x.timestamp, reverse=True)
            context["says_and_reposts"] = say_and_reposts[:10]

            for model, model_name in models_list:
                context[model_name] = model.objects.all().order_by("-timestamp")[:10]

        elif order_by == "random":
            say_ids = list(Say.objects.values_list("id", flat=True))
            repost_ids = list(Repost.objects.values_list("id", flat=True))
            combined_ids = say_ids + repost_ids

            if len(combined_ids) > 10:
                sampled_ids = sample(combined_ids, 10)
            else:
                sampled_ids = combined_ids

            say_sampled = [id for id in sampled_ids if id in say_ids]
            repost_sampled = [id for id in sampled_ids if id in repost_ids]

            say_and_reposts = list(
                chain(
                    Say.objects.filter(id__in=say_sampled),
                    Repost.objects.filter(id__in=repost_sampled),
                )
            )

            context["says_and_reposts"] = say_and_reposts

            for model, model_name in models_list:
                model_ids = list(model.objects.values_list("id", flat=True))

                if len(model_ids) > 10:
                    model_ids = sample(model_ids, 10)

                context[model_name] = model.objects.filter(id__in=model_ids).order_by(
                    "?"
                )

        context["order_by"] = order_by
        context["current_page"] = "All"
        return context


class DiscoverPostListView(ListView):
    template_name = "discover/discover_posts.html"
    paginate_by = 10

    def get_queryset(self):
        return Post.objects.all()  # Default queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_by = self.request.GET.get("order_by", "random")

        if order_by == "trending":
            seven_days_ago = timezone.now() - timedelta(days=7)

            posts = (
                Post.objects.annotate(
                    vote_count=Sum(
                        Case(
                            When(
                                votes__timestamp__gte=seven_days_ago,
                                then=F("votes__value"),
                            ),
                            default=Value(0),
                            output_field=IntegerField(),
                        )
                    )
                )
                .filter(vote_count__gt=-1)
                .order_by("-vote_count", "-timestamp")
            )

        elif order_by == "all_time":
            posts = Post.objects.annotate(
                vote_count=Sum(
                    Case(
                        When(
                            votes__value__isnull=False,
                            then=F("votes__value"),
                        ),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                )
            ).order_by("-vote_count", "-timestamp")

        elif order_by == "newest":
            posts = Post.objects.all().order_by("-timestamp")[:10]

        elif order_by == "random":
            post_ids = list(Post.objects.values_list("id", flat=True))

            if len(post_ids) > 10:
                post_ids = sample(post_ids, 10)

            posts = Post.objects.filter(id__in=post_ids).order_by("?")

        paginator = Paginator(posts, self.paginate_by)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context["posts"] = page_obj
        context["order_by"] = order_by
        context["current_page"] = "Posts"

        # Calculate the starting index for each page
        current_page_number = page_obj.number
        start_index = (current_page_number - 1) * self.paginate_by
        context["start_index"] = start_index + 1

        return context


class DiscoverPinListView(ListView):
    template_name = "discover/discover_pins.html"
    paginate_by = 10

    def get_queryset(self):
        return Pin.objects.all()  # Default queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_by = self.request.GET.get("order_by", "random")

        pins = None
        if order_by == "trending":
            seven_days_ago = timezone.now() - timedelta(days=7)
            pins = Pin.objects.annotate(
                vote_count=Sum(
                    Case(
                        When(
                            votes__timestamp__gte=seven_days_ago,
                            then=F("votes__value"),
                        ),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                )
            ).order_by("-vote_count", "-timestamp")

        elif order_by == "all_time":
            pins = Pin.objects.annotate(
                vote_count=Sum(
                    Case(
                        When(
                            votes__value__isnull=False,
                            then=F("votes__value"),
                        ),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                )
            ).order_by("-vote_count", "-timestamp")

        elif order_by == "newest":
            pins = Pin.objects.all().order_by("-timestamp")

        elif order_by == "random":
            pin_ids = list(Pin.objects.values_list("id", flat=True))
            pin_ids = sample(pin_ids, len(pin_ids))
            pins = Pin.objects.filter(id__in=pin_ids).order_by("?")

        paginator = Paginator(pins, self.paginate_by)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context["pins"] = page_obj
        context["order_by"] = order_by
        context["current_page"] = "Pins"

        # Calculate the starting index for each page
        current_page_number = page_obj.number
        start_index = (current_page_number - 1) * self.paginate_by
        context["start_index"] = start_index + 1

        return context


class DiscoverLuvListListView(ListView):
    template_name = "discover/discover_luvlists.html"
    paginate_by = 10

    def get_queryset(self):
        return LuvList.objects.all()  # Default queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_by = self.request.GET.get("order_by", "random")

        lists = None
        if order_by == "trending":
            seven_days_ago = timezone.now() - timedelta(days=7)
            lists = LuvList.objects.annotate(
                vote_count=Sum(
                    Case(
                        When(
                            votes__timestamp__gte=seven_days_ago,
                            then=F("votes__value"),
                        ),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                )
            ).order_by("-vote_count", "-timestamp")

        elif order_by == "all_time":
            lists = LuvList.objects.annotate(
                vote_count=Sum(
                    Case(
                        When(
                            votes__value__isnull=False,
                            then=F("votes__value"),
                        ),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                )
            ).order_by("-vote_count", "-timestamp")

        elif order_by == "newest":
            lists = LuvList.objects.all().order_by("-timestamp")

        elif order_by == "random":
            list_ids = list(LuvList.objects.values_list("id", flat=True))

            if len(list_ids) > 10:
                list_ids = sample(list_ids, 10)

            lists = LuvList.objects.filter(id__in=list_ids).order_by("?")

        paginator = Paginator(lists, self.paginate_by)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context["lists"] = page_obj
        context["order_by"] = order_by
        context["current_page"] = "Lists"

        # Calculate the starting index for each page
        current_page_number = page_obj.number
        start_index = (current_page_number - 1) * self.paginate_by
        context["start_index"] = start_index + 1
        return context


class DiscoverLikedView(ListView):
    template_name = "discover/discover_liked.html"

    def get_queryset(self):
        return None  # We override `get_context_data` to send multiple querysets

    def fetch_voted_objects(self, model):
        content_type = ContentType.objects.get_for_model(model)
        voted_ids = Vote.objects.filter(
            user=self.request.user, content_type=content_type
        ).values_list("object_id", flat=True)

        return (
            model.objects.filter(id__in=voted_ids)
            .annotate(vote_timestamp=F("votes__timestamp"))
            .order_by("-vote_timestamp")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        models_list = [
            (Post, "posts"),
            (Pin, "pins"),
            (LuvList, "lists"),
            (ReadCheckIn, "read_checkins"),
            (WatchCheckIn, "watch_checkins"),
            (ListenCheckIn, "listen_checkins"),
            (GameCheckIn, "game_checkins"),
        ]

        say_and_reposts = list(
            chain(
                self.fetch_voted_objects(Say),
                self.fetch_voted_objects(Repost),
            )
        )
        context["says_and_reposts"] = sorted(
            say_and_reposts, key=lambda x: x.vote_timestamp, reverse=True
        )

        for model, model_name in models_list:
            context[model_name] = self.fetch_voted_objects(model)

        context["current_page"] = "Liked"
        context["object"] = self.request.user
        return context
