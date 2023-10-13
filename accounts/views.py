import re
import time
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.db.models import Count, Min, OuterRef, Q, Subquery
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from activity_feed.models import Activity, Follow
from entity.models import Person
from listen.models import Audiobook, ListenCheckIn, Podcast, Release, Track
from listen.models import Work as MusicWork
from play.models import Game, GameCast, GameCheckIn, GameRole
from play.models import Work as GameWork
from read.models import Book, BookSeries
from read.models import Instance as LitInstance
from read.models import Periodical, ReadCheckIn
from read.models import Work as LitWork
from watch.models import Movie, Series, WatchCheckIn
from write.models import Comment, LuvList, Pin, Post, Repost, Say, Tag

from .forms import (
    CustomUserChangeForm,
    CustomUserCreationForm,
    EmailRequestForm,
    InvitationRequestForm,
)
from .models import InvitationCode, InvitationRequest

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
        ).order_by("-timestamp")[:15]
        read = latest_read_checkins.filter(
            status__in=["finished_reading", "reread"]
        ).order_by("-timestamp")[:15]
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
        )[:15]
        listening = latest_listen_checkins.filter(status="listening").order_by(
            "-timestamp"
        )[:15]
        listened = latest_listen_checkins.filter(status="listened").order_by(
            "-timestamp"
        )[:15]
        to_listen = latest_listen_checkins.filter(status="to_listen").order_by(
            "-timestamp"
        )[:15]
        subscribed = latest_listen_checkins.filter(status="subscribed").order_by(
            "-timestamp"
        )[:15]

        context["looping"] = looping
        context["listening"] = listening
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
        ).order_by("-timestamp")[:15]
        watched = latest_watch_checkins.filter(
            status__in=["watched", "rewatched"]
        ).order_by("-timestamp")[:15]
        to_watch = latest_watch_checkins.filter(status="to_watch").order_by(
            "-timestamp"
        )[:15]

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
        ).order_by("-timestamp")[:15]
        played = latest_play_checkins.filter(
            status__in=["played", "replayed"]
        ).order_by("-timestamp")[:15]
        to_play = latest_play_checkins.filter(status="to_play").order_by("-timestamp")[
            :15
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


class RequestInvitationView(View):
    BLACKLISTED_DOMAINS = ["example.com", "data-backup-store.com"]

    def post(self, request):
        email = request.POST.get("email")
        if email:
            # Extract the domain from the email address
            domain = email.split("@")[-1]

            # Check if the domain is blacklisted
            if domain in self.BLACKLISTED_DOMAINS:
                return HttpResponseBadRequest("Email domain is blacklisted")

            # Create or get the invitation request
            InvitationRequest.objects.get_or_create(email=email)
            return redirect("accounts:invitation_requested", email=email)

        return redirect("login")


class InvitationRequestedView(View):
    template_name = "accounts/invitation_requested.html"
    form_class = InvitationRequestForm

    def get(self, request, email):
        invitation_request, created = InvitationRequest.objects.get_or_create(
            email=email
        )
        form = self.form_class(instance=invitation_request)
        return render(request, self.template_name, {"form": form})

    def post(self, request, email):
        invitation_request = get_object_or_404(InvitationRequest, email=email)
        form = self.form_class(request.POST, instance=invitation_request)
        if form.is_valid():
            form.save()
            return redirect("accounts:invitation_requested_success")
        return render(request, self.template_name, {"form": form})


class InvitationRequestedSuccessView(TemplateView):
    template_name = "accounts/invitation_requested_success.html"


##########
# Search #
##########


# Filter for 'user' models
def filter_users(query, search_terms):
    results = User.objects.all()
    for term in search_terms:
        results = results.filter(
            Q(username__icontains=term)
            | Q(display_name__icontains=term)
            | Q(bio__icontains=term)
        ).distinct()
    return results


def filter_write(query, search_terms):
    post_results = Post.objects.all()
    say_results = Say.objects.all()
    pin_results = Pin.objects.all()
    repost_results = Repost.objects.all()
    luvlist_results = LuvList.objects.all()

    for term in search_terms:
        post_results = (
            post_results.filter(Q(title__icontains=term) | Q(content__icontains=term))
            .distinct()
            .order_by("timestamp")
        )
        say_results = (
            say_results.filter(content__icontains=term).distinct().order_by("timestamp")
        )
        pin_results = (
            pin_results.filter(
                Q(title__icontains=term)
                | Q(content__icontains=term)
                | Q(url__icontains=term)
            )
            .distinct()
            .order_by("timestamp")
        )
        repost_results = (
            repost_results.filter(content__icontains=term)
            .distinct()
            .order_by("timestamp")
        )
        luvlist_results = (
            luvlist_results.filter(description__icontains=term)
            .distinct()
            .order_by("timestamp")
        )

    return post_results, say_results, pin_results, repost_results, luvlist_results


def filter_read(query, search_terms):
    litwork_results = LitWork.objects.all()
    litinstance_results = LitInstance.objects.all()
    book_results = Book.objects.all()
    periodical_results = Periodical.objects.all()
    book_series = BookSeries.objects.all()

    for term in search_terms:
        litwork_results = (
            litwork_results.filter(
                Q(title__icontains=term)
                | Q(subtitle__icontains=term)
                | Q(workrole__person__name__icontains=term)
                | Q(workrole__person__other_names__icontains=term)
                | Q(workrole__alt_name__icontains=term)
                | Q(publication_date__icontains=term)
            )
            .distinct()
            .order_by("publication_date")
        )
        litinstance_results = (
            litinstance_results.filter(
                Q(title__icontains=term)
                | Q(subtitle__icontains=term)
                | Q(instancerole__person__name__icontains=term)
                | Q(instancerole__person__other_names__icontains=term)
                | Q(instancerole__alt_name__icontains=term)
                | Q(publication_date__icontains=term)
            )
            .distinct()
            .order_by("publication_date")
        )
        book_results = (
            book_results.filter(
                Q(title__icontains=term)
                | Q(subtitle__icontains=term)
                | Q(isbn_10__icontains=term)
                | Q(isbn_13__icontains=term)
                | Q(eisbn_13__icontains=term)
                | Q(asin__icontains=term)
                | Q(bookrole__person__name__icontains=term)
                | Q(bookrole__person__other_names__icontains=term)
                | Q(bookrole__alt_name__icontains=term)
                | Q(publication_date__icontains=term)
                | Q(publisher__name__icontains=term)
            )
            .distinct()
            .order_by("publication_date")
        )
        periodical_results = periodical_results.filter(title__icontains=term).distinct()
        book_series = book_series.filter(Q(title__icontains=term)).distinct()

    return (
        litwork_results,
        litinstance_results,
        book_results,
        periodical_results,
        book_series,
    )


def filter_listen(query, search_terms):
    musicwork_results = MusicWork.objects.all()
    track_results = Track.objects.all()
    release_results = Release.objects.all()
    podcast_results = Podcast.objects.all()
    audiobook_results = Audiobook.objects.all()

    for term in search_terms:
        musicwork_results = (
            musicwork_results.filter(
                Q(title__icontains=term)
                | Q(other_titles__icontains=term)
                | Q(workrole__person__name__icontains=term)
                | Q(workrole__person__other_names__icontains=term)
                | Q(workrole__alt_name__icontains=term)
            )
            .distinct()
            .order_by("release_date")
        )
        track_results = (
            track_results.filter(
                Q(title__icontains=term)
                | Q(other_titles__icontains=term)
                | Q(trackrole__person__name__icontains=term)
                | Q(trackrole__person__other_names__icontains=term)
                | Q(trackrole__alt_name__icontains=term)
            )
            .distinct()
            .order_by("release_date")
        )
        release_results = (
            release_results.filter(
                Q(title__icontains=term)
                | Q(other_titles__icontains=term)
                | Q(releaserole__person__name__icontains=term)
                | Q(releaserole__person__other_names__icontains=term)
                | Q(releaserole__alt_name__icontains=term)
                | Q(catalog_number__icontains=term)
                | Q(label__name__icontains=term)
            )
            .distinct()
            .order_by("release_date")
        )
        podcast_results = podcast_results.filter(Q(title__icontains=term)).distinct()
        audiobook_results = audiobook_results.filter(
            Q(title__icontains=term)
            | Q(audiobookrole__person__name__icontains=term)
            | Q(audiobookrole__person__other_names__icontains=term)
            | Q(release_date__icontains=term)
            | Q(publisher__name__icontains=term)
        ).distinct()

    return (
        musicwork_results,
        track_results,
        release_results,
        podcast_results,
        audiobook_results,
    )


def filter_play(query, search_terms):
    gamework_results = GameWork.objects.all()
    game_results = Game.objects.all()

    for term in search_terms:
        gamework_results = (
            gamework_results.filter(
                Q(title__icontains=term)
                | Q(other_titles__icontains=term)
                | Q(workrole__person__name__icontains=term)
                | Q(workrole__person__other_names__icontains=term)
                | Q(workrole__alt_name__icontains=term)
                | Q(first_release_date=query)
            )
            .distinct()
            .order_by("first_release_date")
        )
        game_results = (
            game_results.filter(
                Q(title__icontains=term)
                | Q(other_titles__icontains=term)
                | Q(developers__name__icontains=term)
                | Q(platforms__name__icontains=term)
                | Q(gameroles__person__name__icontains=term)
                | Q(gameroles__person__other_names__icontains=term)
                | Q(gameroles__alt_name__icontains=term)
                | Q(gamecasts__person__name__icontains=term)
                | Q(gamecasts__person__other_names__icontains=term)
                | Q(gamecasts__character_name__icontains=term)
            )
            .distinct()
            .annotate(earliest_release_date=Min("region_release_dates__release_date"))
            .order_by("earliest_release_date")
        )
    return gamework_results, game_results


def filter_watch(query, search_terms):
    movie_results = Movie.objects.all()
    series_results = Series.objects.all()

    for term in search_terms:
        movie_results = (
            movie_results.filter(
                Q(title__icontains=term)
                | Q(other_titles__icontains=term)
                | Q(movieroles__person__name__icontains=term)
                | Q(movieroles__person__other_names__icontains=term)
                | Q(movieroles__alt_name__icontains=term)
                | Q(moviecasts__person__name__icontains=term)
                | Q(moviecasts__person__other_names__icontains=term)
                | Q(moviecasts__character_name__icontains=term)
            )
            .distinct()
            .annotate(earliest_release_date=Min("region_release_dates__release_date"))
            .order_by("earliest_release_date")
        )
        series_results = (
            series_results.filter(
                Q(title__icontains=term)
                | Q(other_titles__icontains=term)
                | Q(seriesroles__person__name__icontains=term)
                | Q(seriesroles__person__other_names__icontains=term)
                | Q(seriesroles__alt_name__icontains=term)
                | Q(episodes__episodecasts__person__name__icontains=term)
                | Q(episodes__episodecasts__person__other_names__icontains=term)
                | Q(episodes__episodecasts__character_name__icontains=term)
            )
            .distinct()
            .order_by("release_date")
        )

    return movie_results, series_results


def filter_person(query, search_terms):
    person_results = Person.objects.all()

    for term in search_terms:
        person_results = person_results.filter(
            Q(name__icontains=term) | Q(other_names__icontains=term)
        ).distinct()

    return person_results


def parse_query(query):
    pattern = r"\"[^\"]+\"|\'[^\']+\'|“[^”]+”|‘[^’]+’|\S+"
    return [term.strip("\"'“”‘’") for term in re.findall(pattern, query)]


def search_view(request):
    start_time = time.time()

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
    luvlist_results = []
    # read
    litwork_results = []
    litinstance_results = []
    book_results = []
    periodical_results = []
    book_series = []
    # play
    gamework_results = []
    game_results = []
    # listen
    musicwork_results = []
    track_results = []
    release_results = []
    podcast_results = []
    audiobook_results = []
    # watch
    movie_results = []
    series_results = []

    search_terms = parse_query(query)

    if query:
        if model in ["all", "user"]:
            user_results = filter_users(query, search_terms)

        if model in ["all", "write"]:
            (
                post_results,
                say_results,
                pin_results,
                repost_results,
                luvlist_results,
            ) = filter_write(query, search_terms)

        if model in ["all", "read"]:
            (
                litwork_results,
                litinstance_results,
                book_results,
                periodical_results,
                book_series,
            ) = filter_read(query, search_terms)

        if model in ["all", "listen"]:
            (
                musicwork_results,
                track_results,
                release_results,
                podcast_results,
                audiobook_results,
            ) = filter_listen(query, search_terms)

        if model in ["all", "play"]:
            gamework_results, game_results = filter_play(query, search_terms)

        if model in ["all", "watch"]:
            movie_results, series_results = filter_watch(query, search_terms)

        if model in ["all", "person"]:
            person_results = filter_person(query, search_terms)

    execution_time = time.time() - start_time

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
            "luvlist_results": luvlist_results,
            # read
            "litwork_results": litwork_results,
            "litinstance_results": litinstance_results,
            "book_results": book_results,
            "periodical_results": periodical_results,
            "book_series": book_series,
            # play
            "gamework_results": gamework_results,
            "game_results": game_results,
            # listen
            "musicwork_results": musicwork_results,
            "track_results": track_results,
            "release_results": release_results,
            "podcast_results": podcast_results,
            "audiobook_results": audiobook_results,
            # watch
            "movie_results": movie_results,
            "series_results": series_results,
            # other
            "execution_time": execution_time,
            "terms": search_terms,
        },
    )


@login_required
def get_followed_usernames(request):
    follows = Follow.objects.filter(follower=request.user).values(
        "followed__username", "followed__display_name"
    )
    usernames_with_display_names = [
        {
            "username": follow["followed__username"],
            "display_name": follow["followed__display_name"],
        }
        for follow in follows
    ]
    return JsonResponse({"usernames_with_display_names": usernames_with_display_names})


@login_required
def get_user_tags(request):
    user = request.user

    # Get ContentType for each model
    comment_ct = ContentType.objects.get_for_model(Comment)
    repost_ct = ContentType.objects.get_for_model(Repost)
    post_ct = ContentType.objects.get_for_model(Post)
    say_ct = ContentType.objects.get_for_model(Say)
    pin_ct = ContentType.objects.get_for_model(Pin)
    readcheckin_ct = ContentType.objects.get_for_model(ReadCheckIn)
    listencheckin_ct = ContentType.objects.get_for_model(ListenCheckIn)
    watchcheckin_ct = ContentType.objects.get_for_model(WatchCheckIn)
    gamecheckin_ct = ContentType.objects.get_for_model(GameCheckIn)

    # Combine all content types into a list
    all_cts = [
        comment_ct,
        repost_ct,
        post_ct,
        say_ct,
        pin_ct,
        readcheckin_ct,
        listencheckin_ct,
        watchcheckin_ct,
        gamecheckin_ct,
    ]

    # Initialize an empty list to store unique tags
    unique_tags = []

    # Loop through each ContentType and get tags
    for ct in all_cts:
        tags = (
            Tag.objects.filter(
                **{
                    f"{ct.model.lower()}__user": user,  # Dynamic field name based on model
                    f"{ct.model.lower()}__tags__isnull": False,  # Ensure tags field is not empty
                }
            )
            .values("name")
            .annotate(tag_count=Count("name"))
            .order_by("-tag_count")
        )

        # Add tags to unique_tags list if not already present
        for tag in tags:
            if tag["name"] not in unique_tags:
                unique_tags.append(tag["name"])

    return JsonResponse({"tags": unique_tags})
