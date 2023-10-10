from datetime import timedelta

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
from write.models import LuvList, Pin, Post, Say

from .models import Vote

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
        order_by = self.request.GET.get("order_by", "newest")  # Default to 'newest'
        models_list = [
            (Say, "says"),
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

            for model, model_name in models_list:
                context[model_name] = (
                    self.annotate_vote_count(model, time_condition)
                    .filter(vote_count__gt=-1)
                    .order_by("-vote_count")
                )[:10]

        elif order_by == "all_time":
            time_condition = None

            for model, model_name in models_list:
                context[model_name] = (
                    self.annotate_vote_count(model, time_condition).order_by(
                        "-vote_count", "-timestamp"
                    )
                )[:10]

        elif order_by == "newest":
            for model, model_name in models_list:
                context[model_name] = model.objects.all().order_by("-timestamp")[:10]

        context["order_by"] = order_by
        return context


class DiscoverPostListView(ListView):
    template_name = "discover/discover_posts.html"
    paginate_by = 10

    def get_queryset(self):
        return Post.objects.all()  # Default queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_by = self.request.GET.get("order_by", "trending")  # Default to 'votes'

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
                .order_by("-vote_count")
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

        paginator = Paginator(posts, self.paginate_by)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context["posts"] = page_obj
        context["order_by"] = order_by
        return context


class DiscoverPinListView(ListView):
    template_name = "discover/discover_pins.html"
    paginate_by = 10

    def get_queryset(self):
        return Pin.objects.all()  # Default queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_by = self.request.GET.get("order_by", "trending")

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
            ).order_by("-vote_count")

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

        paginator = Paginator(pins, self.paginate_by)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context["pins"] = page_obj
        context["order_by"] = order_by
        return context


class DiscoverLuvListListView(ListView):
    template_name = "discover/discover_luvlists.html"
    paginate_by = 10

    def get_queryset(self):
        return LuvList.objects.all()  # Default queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_by = self.request.GET.get("order_by", "trending")

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
            ).order_by("-vote_count")

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

        paginator = Paginator(lists, self.paginate_by)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context["lists"] = page_obj
        context["order_by"] = order_by
        return context
