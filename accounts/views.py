from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import serializers
from django.db.models import OuterRef, Q, Subquery
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from activity_feed.models import Activity, Follow
from entity.models import Person
from listen.models import ListenCheckIn, Podcast, Release, Track
from listen.models import Work as MusicWork
from play.models import Game, GameCast, GameCheckIn, GameRole
from play.models import Work as GameWork
from read.models import Book
from read.models import Instance as LitInstance
from read.models import Periodical, ReadCheckIn
from read.models import Work as LitWork
from watch.models import Movie, Series, WatchCheckIn
from write.models import Pin, Post, Repost, Say

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import InvitationCode

TIME_RESTRICTION = 30  # time restriction for generating invitation codes
JOINING_TIME_RESTRICTION = 30
User = get_user_model()


@login_required
def redirect_to_profile(request):
    return redirect("accounts:detail", username=request.user.username)


class SignUpView(CreateView):
    """View for user signup."""

    form_class = CustomUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        self.object = form.save()
        # set invitation code as used
        if self.object.code_used:  # Check if the user used a code
            self.object.code_used.is_used = True
            self.object.code_used.save()

        return super().form_valid(form)


class AccountDetailView(DetailView):
    """Detail view for user accounts."""

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"
    template_name = "accounts/account_detail.html"

    def dispatch(self, request, *args, **kwargs):
        # Get the User object
        user = get_object_or_404(User, username=self.kwargs["username"])
        # If the user's profile isn't public and the current user isn't authenticated, raise a 404 error
        if not user.is_public and not request.user.is_authenticated:
            return redirect("{}?next={}".format(reverse("login"), request.path))
        # Otherwise, proceed as normal
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check if the user has already generated an invitation code within the time restriction
        start_date = timezone.now() - timedelta(days=TIME_RESTRICTION)
        if self.request.user.is_authenticated:
            code_recently_generated = self.request.user.codes_generated.filter(
                generated_at__gte=start_date
            ).first()

            # Check if the code is used
            if code_recently_generated and code_recently_generated.is_used:
                context["can_generate_code"] = False
            else:
                context["can_generate_code"] = True
        else:
            context["can_generate_code"] = False

        user_posts = self.object.post_set.all().order_by("-timestamp")
        user_pins = self.object.pin_set.all().order_by("-timestamp")
        user_says = self.object.say_set.all().order_by("-timestamp")
        context["posts"] = user_posts
        context["pins"] = user_pins
        context["says"] = user_says
        context["recent_activities"] = Activity.objects.filter(
            user=self.object
        ).order_by("-timestamp")[:3]
        context["recent_following"] = Follow.objects.filter(
            follower=self.object
        ).order_by("-timestamp")[:6]
        context["recent_followers"] = Follow.objects.filter(
            followed=self.object
        ).order_by("-timestamp")[:6]

        context["no_citation_css"] = True
        context["no_text_input"] = True

        # First, get the latest check-in for each book
        latest_read_checkins = ReadCheckIn.objects.filter(
            user=self.object,
            timestamp=Subquery(
                ReadCheckIn.objects.filter(
                    user=self.object,
                    content_type=OuterRef("content_type"),
                    object_id=OuterRef("object_id"),
                )
                .order_by("-timestamp")
                .values("timestamp")[:1]
            ),
        )

        # Then, filter the latest check-ins for each category
        reading = latest_read_checkins.filter(
            status__in=["reading", "rereading"]
        ).order_by("-timestamp")[:6]
        read = latest_read_checkins.filter(
            status__in=["finished_reading", "reread"]
        ).order_by("-timestamp")[:6]
        to_read = latest_read_checkins.filter(status="to_read").order_by("-timestamp")[
            :6
        ]

        context["reading"] = reading
        context["read"] = read
        context["to_read"] = to_read
        context["does_read_exist"] = read.exists() or reading.exists()

        latest_listen_checkins = ListenCheckIn.objects.filter(
            user=self.object,
            timestamp=Subquery(
                ListenCheckIn.objects.filter(
                    user=self.object,
                    content_type=OuterRef("content_type"),
                    object_id=OuterRef("object_id"),
                )
                .order_by("-timestamp")
                .values("timestamp")[:1]
            ),
        )

        # Then, filter the latest check-ins for each category and limit the results
        looping = latest_listen_checkins.filter(status="looping").order_by(
            "-timestamp"
        )[:6]
        listened = latest_listen_checkins.filter(status="listened").order_by(
            "-timestamp"
        )[:6]
        to_listen = latest_listen_checkins.filter(status="to_listen").order_by(
            "-timestamp"
        )[:6]
        subscribed = latest_listen_checkins.filter(status="subscribed").order_by(
            "-timestamp"
        )[:6]

        context["looping"] = looping
        context["listened"] = listened
        context["to_listen"] = to_listen
        context["subscribed"] = subscribed
        context["does_listen_exist"] = listened.exists() or looping.exists()

        # First, get the latest check-in for each show
        latest_watch_checkins = WatchCheckIn.objects.filter(
            user=self.object,
            timestamp=Subquery(
                WatchCheckIn.objects.filter(
                    user=self.object,
                    content_type=OuterRef("content_type"),
                    object_id=OuterRef("object_id"),
                )
                .order_by("-timestamp")
                .values("timestamp")[:1]
            ),
        )

        # Then, filter the latest check-ins for each category and limit the results
        watching = latest_watch_checkins.filter(
            status__in=["watching", "rewatching"]
        ).order_by("-timestamp")[:6]
        watched = latest_watch_checkins.filter(
            status__in=["watched", "rewatched"]
        ).order_by("-timestamp")[:6]
        to_watch = latest_watch_checkins.filter(status="to_watch").order_by(
            "-timestamp"
        )[:6]

        context["watching"] = watching
        context["watched"] = watched
        context["to_watch"] = to_watch
        context["does_watch_exist"] = watched.exists() or watching.exists()

        # First, get the latest check-in for each game
        latest_play_checkins = GameCheckIn.objects.filter(
            user=self.object,
            timestamp=Subquery(
                GameCheckIn.objects.filter(user=self.object, game=OuterRef("game"))
                .order_by("-timestamp")
                .values("timestamp")[:1]
            ),
        )

        # Then, filter the latest check-ins for each category and limit the results
        playing = latest_play_checkins.filter(
            status__in=["playing", "replaying"]
        ).order_by("-timestamp")[:6]
        played = latest_play_checkins.filter(
            status__in=["played", "replayed"]
        ).order_by("-timestamp")[:6]
        to_play = latest_play_checkins.filter(status="to_play").order_by("-timestamp")[
            :6
        ]

        context["playing"] = playing
        context["played"] = played
        context["to_play"] = to_play
        context["does_play_exist"] = played.exists() or playing.exists()

        return context


class AccountUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = CustomUserChangeForm
    template_name = "accounts/account_update.html"
    slug_field = "username"
    slug_url_kwarg = "username"
    success_url = reverse_lazy("accounts:profile")

    def get_initial(self):
        initial = super().get_initial()
        initial["timezone"] = self.request.user.timezone
        return initial

    def get_object(self, queryset=None):
        return self.request.user


class GenerateInvitationCodeView(View):
    def post(self, request):
        user = request.user
        # Check if the user joined less than JOINING_TIME_RESTRICTION days ago
        if (timezone.now() - user.date_joined).days < JOINING_TIME_RESTRICTION:
            messages.error(
                request,
                "You can start inviting friends {} days after you join.".format(
                    JOINING_TIME_RESTRICTION
                ),
            )
            return redirect("accounts:profile")

        # Check if there is an unused code generated by the user
        unused_code = user.codes_generated.filter(is_used=False).first()
        if unused_code:
            code = unused_code
        elif not user.codes_generated.filter(
            generated_at__gte=timezone.now() - timedelta(days=TIME_RESTRICTION)
        ).exists():
            # User has not generated a code this month, so generate a new one
            code = InvitationCode.objects.create(generated_by=user)
        else:
            # User has already generated a code this month
            messages.error(
                request, "You can only generate one invitation code per month."
            )
            return redirect("accounts:profile")
        messages.success(
            request,
            mark_safe(
                f'Send this invitation code to your friend: <strong style="color:blue;">{code.code}</strong>.'
            ),
        )
        messages.success(request, "Every invitation code can only be used once. ")
        messages.success(request, "You can only invite one friend every month. ")
        return redirect("accounts:profile")


def home(request, *args, **kwargs):
    if request.user.is_authenticated:
        return redirect("activity_feed:activity_feed")
    else:
        return redirect("login")


def search_view(request):
    query = request.GET.get("q")
    model = request.GET.get("model", "all")

    # Initialize all results as empty
    user_results = []
    # entity
    person_results = []
    # write
    post_results = []
    say_results = []
    pin_results = []
    repost_results = []
    # read
    litwork_results = []
    litinstance_results = []
    book_results = []
    periodical_results = []
    # play
    gamework_results = []
    game_results = []
    # listen
    musicwork_results = []
    track_results = []
    release_results = []
    podcast_results = []
    # watch
    movie_results = []
    series_results = []

    if query:
        if model in ["all", "write"]:
            user_results = User.objects.filter(
                Q(username__icontains=query)
                | Q(display_name__icontains=query)
                | Q(bio__icontains=query)
            )
            post_results = Post.objects.filter(
                Q(title__icontains=query) | Q(content__icontains=query)
            ).distinct()
            say_results = Say.objects.filter(content__icontains=query).distinct()
            pin_results = Pin.objects.filter(
                Q(title__icontains=query)
                | Q(content__icontains=query)
                | Q(url__icontains=query)
            ).distinct()
            repost_results = Repost.objects.filter(content__icontains=query).distinct()

        if model in ["all", "read"]:
            litwork_results = LitWork.objects.filter(
                Q(title__icontains=query)
                | Q(workrole__person__name__icontains=query)
                | Q(workrole__alt_name__icontains=query)
                | Q(publication_date__icontains=query)
            ).distinct()
            litinstance_results = LitInstance.objects.filter(
                Q(title__icontains=query)
                | Q(instancerole__person__name__icontains=query)
                | Q(instancerole__alt_name__icontains=query)
                | Q(publication_date__icontains=query)
            ).distinct()
            book_results = Book.objects.filter(
                Q(title__icontains=query)
                | Q(isbn_10__icontains=query)
                | Q(isbn_13__icontains=query)
                | Q(eisbn_13__icontains=query)
                | Q(asin__icontains=query)
                | Q(bookrole__person__name__icontains=query)
                | Q(bookrole__alt_name__icontains=query)
                | Q(publication_date__icontains=query)
            ).distinct()
            periodical_results = Periodical.objects.filter(
                title__icontains=query
            ).distinct()  # Update with your real query

        if model in ["all", "listen"]:
            musicwork_results = MusicWork.objects.filter(
                Q(title__icontains=query)
                | Q(other_titles__icontains=query)
                | Q(workrole__person__name__icontains=query)
                | Q(workrole__alt_name__icontains=query)
            ).distinct()  # Update with your real query
            track_results = Track.objects.filter(
                Q(title__icontains=query)
                | Q(other_titles__icontains=query)
                | Q(trackrole__person__name__icontains=query)
                | Q(trackrole__alt_name__icontains=query)
            ).distinct()  # Update with your real query
            release_results = Release.objects.filter(
                Q(title__icontains=query)
                | Q(other_titles__icontains=query)
                | Q(releaserole__person__name__icontains=query)
                | Q(releaserole__alt_name__icontains=query)
                | Q(catalog_number__icontains=query)
            ).distinct()  # Update with your real query
            podcast_results = Podcast.objects.filter(
                Q(title__icontains=query)
            ).distinct()

        if model in ["all", "play"]:
            gamework_results = GameWork.objects.filter(
                Q(title__icontains=query)
                | Q(workrole__person__name__icontains=query)
                | Q(workrole__alt_name__icontains=query)
                | Q(first_release_date=query)
            ).distinct()
            game_results = Game.objects.filter(
                Q(title__icontains=query)
                | Q(developers__name__icontains=query)
                | Q(platforms__name__icontains=query)
                | Q(release_date__icontains=query)
                | Q(gameroles__person__name__icontains=query)
                | Q(gameroles__alt_name__icontains=query)
            ).distinct()  # Update with your real query

        if model in ["all", "watch"]:
            movie_results = Movie.objects.filter(
                Q(title__icontains=query)
                | Q(other_titles__icontains=query)
                | Q(movieroles__person__name__icontains=query)
                | Q(movieroles__alt_name__icontains=query)
                | Q(moviecasts__person__name__icontains=query)
                | Q(moviecasts__character_name__icontains=query)
                | Q(release_date__icontains=query)
            ).distinct()
            series_results = Series.objects.filter(
                Q(title__icontains=query)
                | Q(other_titles__icontains=query)
                | Q(seriesroles__person__name__icontains=query)
                | Q(seriesroles__alt_name__icontains=query)
                | Q(episodes__episodecasts__person__name__icontains=query)
                | Q(episodes__episodecasts__character_name__icontains=query)
            ).distinct()

        if model in ["all", "person"]:
            person_results = Person.objects.filter(
                Q(name__icontains=query) | Q(other_names__icontains=query)
            ).distinct()

    return render(
        request,
        "accounts/search_results.html",
        {
            "query": query,
            "user_results": user_results,
            # entity
            "person_results": person_results,
            # write
            "post_results": post_results,
            "say_results": say_results,
            "pin_results": pin_results,
            "repost_results": repost_results,
            # read
            "litwork_results": litwork_results,
            "litinstance_results": litinstance_results,
            "book_results": book_results,
            "periodical_results": periodical_results,
            # play
            "gamework_results": gamework_results,
            "game_results": game_results,
            # listen
            "musicwork_results": musicwork_results,
            "track_results": track_results,
            "release_results": release_results,
            "podcast_results": podcast_results,
            # watch
            "movie_results": movie_results,
            "series_results": series_results,
        },
    )


class PersonalActivityFeedView(LoginRequiredMixin, ListView):
    model = Activity
    template_name = "activity_feed/activity_feed.html"
    paginate_by = 50

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["feed_type"] = "personal"
        context["no_citation_css"] = True
        username = self.kwargs["username"]
        context["feed_user"] = User.objects.get(username=username)
        return context

    def get_queryset(self):
        # Get the username from the URL
        username = self.kwargs["username"]
        # Get the User object for this username
        user = User.objects.get(username=username)
        # Return only the activities for this user
        return super().get_queryset().filter(user=user).order_by("-timestamp")


class FollowingListView(ListView):
    model = Follow
    template_name = "accounts/following_list.html"
    context_object_name = "following_list"

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs["username"])
        return user.following.all()


class FollowerListView(ListView):
    model = Follow
    template_name = "accounts/follower_list.html"
    context_object_name = "follower_list"

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs["username"])
        return user.followers.all()


@login_required
def export_user_data(request):
    from django.apps import apps

    User = get_user_model()
    user = User.objects.filter(pk=request.user.pk)

    # Use Django's built-in serialization
    data = serializers.serialize("json", user)

    # Get all models in your app
    models = apps.get_models()

    for model in models:
        # Check if the model has a foreign key to User
        if any(f for f in model._meta.fields if f.related_model == User):
            try:
                related_data = model.objects.filter(user=request.user.pk)
                data += serializers.serialize("json", related_data)
            except:
                continue

    # Create a HttpResponse with a 'Content-Disposition' header to suggest a filename
    response = HttpResponse(data, content_type="application/json")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="{request.user.username}_data.json"'

    return response


@login_required
def export_game_data(request):
    User = get_user_model()

    # filter Games created by this user
    games = Game.objects.filter(created_by=request.user)

    # Use Django's built-in serialization
    data = serializers.serialize("json", games)

    # get all related data for each game
    for game in games:
        developers = game.developers.all()
        data += serializers.serialize("json", developers)

        persons_as_gamerole = GameRole.objects.filter(game=game)
        data += serializers.serialize("json", persons_as_gamerole)

        persons_as_gamecast = GameCast.objects.filter(game=game)
        data += serializers.serialize("json", persons_as_gamecast)

        platforms = game.platforms.all()
        data += serializers.serialize("json", platforms)

    # Create a HttpResponse with a 'Content-Disposition' header to suggest a filename
    response = HttpResponse(data, content_type="application/json")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="{request.user.username}_games_data.json"'

    return response
