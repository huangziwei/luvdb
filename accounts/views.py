import re
import time
from datetime import timedelta
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.db import transaction
from django.db.models import Count, Min, OuterRef, Q, Subquery
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from django_ratelimit.decorators import ratelimit

from accounts.models import CustomUser
from activity_feed.models import Activity, Block, Follow
from entity.models import Company, Creator
from listen.models import Audiobook, ListenCheckIn, Podcast, Release, Track
from listen.models import Work as MusicWork
from play.models import Game, PlayCheckIn
from play.models import Work as GameWork
from read.models import Book, BookSeries
from read.models import Instance as LitInstance
from read.models import Periodical, ReadCheckIn
from read.models import Work as LitWork
from watch.models import Movie, Series, WatchCheckIn
from write.models import Comment, ContentInList, LuvList, Pin, Post, Repost, Say, Tag
from write.utils_formatting import check_required_js

from .forms import (
    AppPasswordForm,
    BlueSkyAccountForm,
    CustomUserChangeForm,
    CustomUserCreationForm,
    InvitationRequestForm,
    MastodonAccountForm,
)
from .models import (
    AppPassword,
    BlueSkyAccount,
    InvitationCode,
    InvitationRequest,
    MastodonAccount,
    WebMention,
)

TIME_RESTRICTION = 7  # time restriction for generating invitation codes
JOINING_TIME_RESTRICTION = 7
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invite_code = self.request.GET.get("code")
        if invite_code:
            context["form"].fields["invitation_code"].initial = invite_code
            context["form"].fields["invitation_code"].widget.attrs["readonly"] = True
            context["form"].fields["invitation_code"].widget.attrs[
                "class"
            ] = "readonly-field"

        return context


class CustomLoginView(LoginView):
    template_name = "registration/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["recent_books"] = Book.objects.order_by("-created_at")[:6]
        context["recent_movies"] = Movie.objects.order_by("-created_at")[:6]
        context["recent_series"] = Series.objects.order_by("-created_at")[:6]
        context["recent_music"] = Release.objects.order_by("-created_at")[:6]
        context["recent_games"] = Game.objects.order_by("-created_at")[:6]

        return context


def get_latest_checkins(user, checkin_model):
    return checkin_model.objects.filter(
        user=user,
        timestamp=Subquery(
            checkin_model.objects.filter(
                content_type=OuterRef("content_type"),
                object_id=OuterRef("object_id"),
                user=user,
            )
            .order_by("-timestamp")
            .values("timestamp")[:1]
        ),
    )


@method_decorator(ratelimit(key="ip", rate="12/m", block=True), name="dispatch")
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
        user = self.object

        context.update(
            {
                "recent_activities": Activity.objects.filter(user=user).order_by(
                    "-timestamp"
                )[:3],
                "recent_following": Follow.objects.filter(follower=user).order_by(
                    "-timestamp"
                )[:6],
            }
        )

        latest_read_checkins = get_latest_checkins(
            user=self.object, checkin_model=ReadCheckIn
        )
        latest_listen_checkins = get_latest_checkins(
            user=self.object, checkin_model=ListenCheckIn
        )
        latest_watch_checkins = get_latest_checkins(
            user=self.object, checkin_model=WatchCheckIn
        )
        latest_play_checkins = get_latest_checkins(
            user=self.object, checkin_model=PlayCheckIn
        )

        reading = latest_read_checkins.filter(
            status__in=["reading", "rereading"]
        ).order_by("-timestamp")[:6]
        read = latest_read_checkins.filter(
            status__in=["finished_reading", "reread", "afterthought"]
        ).order_by("-timestamp")[:6]

        context["reading"] = reading
        context["read"] = read
        context["does_read_exist"] = read.exists() or reading.exists()

        looping = latest_listen_checkins.filter(status="looping").order_by(
            "-timestamp"
        )[:6]
        listening = latest_listen_checkins.filter(
            status__in=["listening", "relistening"]
        ).order_by("-timestamp")[:6]
        listened = latest_listen_checkins.filter(
            status__in=["listened", "relistened"]
        ).order_by("-timestamp")[:6]
        subscribed = latest_listen_checkins.filter(status="subscribed").order_by(
            "-timestamp"
        )[:6]

        context["looping"] = looping
        context["listening"] = listening
        context["listened"] = listened
        context["subscribed"] = subscribed
        context["does_listen_exist"] = listened.exists() or looping.exists()

        watching = latest_watch_checkins.filter(
            status__in=["watching", "rewatching"]
        ).order_by("-timestamp")[:6]
        watched = latest_watch_checkins.filter(
            status__in=["watched", "rewatched"]
        ).order_by("-timestamp")[:6]

        context["watching"] = watching
        context["watched"] = watched
        context["does_watch_exist"] = watched.exists() or watching.exists()

        playing = latest_play_checkins.filter(
            status__in=["playing", "replaying"]
        ).order_by("-timestamp")[:6]
        played = latest_play_checkins.filter(
            status__in=["played", "replayed"]
        ).order_by("-timestamp")[:6]

        context["playing"] = playing
        context["played"] = played
        context["does_play_exist"] = played.exists() or playing.exists()

        # Check each activity item for both MathJax and Mermaid requirements
        include_mathjax, include_mermaid = check_required_js(
            context["recent_activities"]
        )

        # Add the flags to the context
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid
        context["no_citation_css"] = True

        # Check if the user is blocked
        context["is_blocked"] = (
            Block.objects.filter(blocker=user, blocked=self.request.user).exists()
            if self.request.user.is_authenticated
            else False
        )

        return context


class AccountUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = CustomUserChangeForm
    template_name = "accounts/account_update.html"
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_initial(self):
        initial = super().get_initial()
        initial["timezone"] = self.request.user.timezone
        return initial

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self) -> str:
        return reverse_lazy(
            "accounts:detail", kwargs={"username": self.object.username}
        )


def home(request, *args, **kwargs):
    if request.user.is_authenticated:
        return redirect("activity_feed:activity_feed")
    else:
        return redirect("login")


class PersonalActivityFeedView(ListView):
    model = Activity
    template_name = "activity_feed/activity_feed.html"
    paginate_by = 20

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["feed_type"] = "personal"
        context["no_citation_css"] = True
        username = self.kwargs["username"]
        context["feed_user"] = User.objects.get(username=username)

        # Add the flags to the context
        include_mathjax, include_mermaid = check_required_js(context["page_obj"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        return context

    def get_queryset(self):
        # Get the username from the URL
        username = self.kwargs["username"]
        # Get the User object for this username
        user = User.objects.get(username=username)
        # Return only the activities for this user
        return super().get_queryset().filter(user=user).order_by("-timestamp")


class FollowingListView(UserPassesTestMixin, ListView):
    model = Follow
    template_name = "accounts/following_list.html"
    context_object_name = "following_list"

    def test_func(self):
        user = get_object_or_404(User, username=self.kwargs["username"])
        return self.request.user == user

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs["username"])
        return user.following.all()


@login_required
def export_user_data(request, username):
    from django.apps import apps

    User = get_user_model()
    user = User.objects.filter(username=username)

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
            return redirect("invitation_requested", email=email)

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
            return redirect("invitation_requested_success")
        return render(request, self.template_name, {"form": form})


class InvitationRequestedSuccessView(TemplateView):
    template_name = "accounts/invitation_requested_success.html"


class ManageInvitationRequestsView(UserPassesTestMixin, ListView):
    model = InvitationRequest
    template_name = "accounts/invitation_requested_management.html"
    context_object_name = "invitation_requests"

    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, *args, **kwargs):
        if "delete_id" in request.POST:
            # Handle deletion request
            invitation_id = request.POST.get("delete_id")
            if invitation_id:
                try:
                    invitation = InvitationRequest.objects.get(id=invitation_id)
                    invitation.delete()
                except InvitationRequest.DoesNotExist:
                    pass  # Handle the case where the invitation does not exist
        elif "mark_invite_id" in request.POST:
            # Handle marking as invited
            invitation_id = request.POST.get("mark_invite_id")
            try:
                invitation = InvitationRequest.objects.get(id=invitation_id)
                invitation.is_invited = True
                invitation.save()
            except InvitationRequest.DoesNotExist:
                pass  # Handle non-existent invitation

        return redirect("manage_invitation_requests")


##########
# Search #
##########
def filter_content(queryset, search_terms, content_fields):
    for term in search_terms:
        or_conditions = Q()
        for field in content_fields:
            or_conditions |= Q(**{f"{field}__icontains": term})
        queryset = queryset.filter(or_conditions).distinct().order_by("timestamp")
    return queryset


def filter_self(user, search_terms):
    return (
        filter_content(
            Post.objects.filter(user=user), search_terms, ["title", "content"]
        ),
        filter_content(Say.objects.filter(user=user), search_terms, ["content"]),
        filter_content(
            Pin.objects.filter(user=user), search_terms, ["title", "content", "url"]
        ),
        filter_content(Repost.objects.filter(user=user), search_terms, ["content"]),
        filter_content(LuvList.objects.filter(user=user), search_terms, ["notes"]),
        filter_content(
            ReadCheckIn.objects.filter(user=user), search_terms, ["content"]
        ),
        filter_content(
            WatchCheckIn.objects.filter(user=user), search_terms, ["content"]
        ),
        filter_content(
            ListenCheckIn.objects.filter(user=user), search_terms, ["content"]
        ),
        filter_content(
            PlayCheckIn.objects.filter(user=user), search_terms, ["content"]
        ),
    )


def filter_write(query, search_terms, is_user_authenticated):
    # Apply the is_public filter for non-authenticated users
    if is_user_authenticated:
        post_query = Post.objects.all()
        say_query = Say.objects.all()
        pin_query = Pin.objects.all()
        repost_query = Repost.objects.all()
        luvlist_query = LuvList.objects.all()
        read_checkin_query = ReadCheckIn.objects.all()
        watch_checkin_query = WatchCheckIn.objects.all()
        listen_checkin_query = ListenCheckIn.objects.all()
        play_checkin_query = PlayCheckIn.objects.all()
    else:
        post_query = Post.objects.filter(user__is_public=True)
        say_query = Say.objects.filter(user__is_public=True)
        pin_query = Pin.objects.filter(user__is_public=True)
        repost_query = Repost.objects.filter(user__is_public=True)
        luvlist_query = LuvList.objects.filter(user__is_public=True)
        read_checkin_query = ReadCheckIn.objects.filter(user__is_public=True)
        watch_checkin_query = WatchCheckIn.objects.filter(user__is_public=True)
        listen_checkin_query = ListenCheckIn.objects.filter(user__is_public=True)
        play_checkin_query = PlayCheckIn.objects.filter(user__is_public=True)

    return (
        filter_content(post_query, search_terms, ["title", "content"]),
        filter_content(say_query, search_terms, ["content"]),
        filter_content(pin_query, search_terms, ["title", "content", "url"]),
        filter_content(repost_query, search_terms, ["content"]),
        filter_content(luvlist_query, search_terms, ["notes"]),
        filter_content(read_checkin_query, search_terms, ["content"]),
        filter_content(watch_checkin_query, search_terms, ["content"]),
        filter_content(listen_checkin_query, search_terms, ["content"]),
        filter_content(play_checkin_query, search_terms, ["content"]),
    )


def filter_users(query, search_terms):
    results = User.objects.all()
    for term in search_terms:
        results = (
            results.filter(
                Q(username__icontains=term)
                | Q(display_name__icontains=term)
                | Q(bio__icontains=term)
            )
            .distinct()
            .order_by("username")
        )
    return results


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
                | Q(workrole__creator__name__icontains=term)
                | Q(workrole__creator__other_names__icontains=term)
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
                | Q(instancerole__creator__name__icontains=term)
                | Q(instancerole__creator__other_names__icontains=term)
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
                | Q(bookrole__creator__name__icontains=term)
                | Q(bookrole__creator__other_names__icontains=term)
                | Q(bookrole__alt_name__icontains=term)
                | Q(publication_date__icontains=term)
                | Q(publisher__name__icontains=term)
            )
            .distinct()
            .order_by("publication_date")
        )
        periodical_results = (
            periodical_results.filter(title__icontains=term)
            .distinct()
            .order_by("title")
        )
        book_series = (
            book_series.filter(Q(title__icontains=term)).distinct().order_by("title")
        )

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
                | Q(workrole__creator__name__icontains=term)
                | Q(workrole__creator__other_names__icontains=term)
                | Q(workrole__alt_name__icontains=term)
            )
            .distinct()
            .order_by("release_date")
        )
        track_results = (
            track_results.filter(
                Q(title__icontains=term)
                | Q(other_titles__icontains=term)
                | Q(trackrole__creator__name__icontains=term)
                | Q(trackrole__creator__other_names__icontains=term)
                | Q(trackrole__alt_name__icontains=term)
            )
            .distinct()
            .order_by("release_date")
        )
        release_results = (
            release_results.filter(
                Q(title__icontains=term)
                | Q(other_titles__icontains=term)
                | Q(releaserole__creator__name__icontains=term)
                | Q(releaserole__creator__other_names__icontains=term)
                | Q(releaserole__alt_name__icontains=term)
                | Q(catalog_number__icontains=term)
                | Q(label__name__icontains=term)
            )
            .distinct()
            .order_by("release_date")
        )
        podcast_results = podcast_results.filter(Q(title__icontains=term)).distinct()
        audiobook_results = (
            audiobook_results.filter(
                Q(title__icontains=term)
                | Q(audiobookrole__creator__name__icontains=term)
                | Q(audiobookrole__creator__other_names__icontains=term)
                | Q(release_date__icontains=term)
                | Q(publisher__name__icontains=term)
            )
            .distinct()
            .order_by("release_date")
        )

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
                | Q(workrole__creator__name__icontains=term)
                | Q(workrole__creator__other_names__icontains=term)
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
                | Q(gameroles__creator__name__icontains=term)
                | Q(gameroles__creator__other_names__icontains=term)
                | Q(gameroles__alt_name__icontains=term)
                | Q(gamecasts__creator__name__icontains=term)
                | Q(gamecasts__creator__other_names__icontains=term)
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
                | Q(movieroles__creator__name__icontains=term)
                | Q(movieroles__creator__other_names__icontains=term)
                | Q(movieroles__alt_name__icontains=term)
                | Q(moviecasts__creator__name__icontains=term)
                | Q(moviecasts__creator__other_names__icontains=term)
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
                | Q(seriesroles__creator__name__icontains=term)
                | Q(seriesroles__creator__other_names__icontains=term)
                | Q(seriesroles__alt_name__icontains=term)
                | Q(episodes__episodecasts__creator__name__icontains=term)
                | Q(episodes__episodecasts__creator__other_names__icontains=term)
                | Q(episodes__episodecasts__character_name__icontains=term)
            )
            .distinct()
            .order_by("release_date")
        )

    return movie_results, series_results


def filter_entity(query, search_terms):
    creator_results = Creator.objects.all()
    company_results = Company.objects.all()

    for term in search_terms:
        creator_results = (
            creator_results.filter(
                Q(name__icontains=term) | Q(other_names__icontains=term)
            )
            .distinct()
            .order_by("name")
        )

        company_results = (
            company_results.filter(
                Q(name__icontains=term) | Q(other_names__icontains=term)
            )
            .distinct()
            .order_by("name")
        )

    return creator_results, company_results


def parse_query(query):
    pattern = r"\"[^\"]+\"|\'[^\']+\'|“[^”]+”|‘[^’]+’|\S+"
    return [term.strip("\"'“”‘’") for term in re.findall(pattern, query)]


def search_view(request):
    is_user_authenticated = request.user.is_authenticated

    last_search_time = request.session.get("last_search_time")

    start_time = time.time()

    if last_search_time and (start_time - last_search_time) < 2:
        return render(request, "429.html", status=429)
    request.session["last_search_time"] = start_time

    query = request.GET.get("q")
    model = request.GET.get("model", "all")

    # Initialize all results as empty
    user_results = []
    # entity
    creator_results = []
    company_results = []
    # write
    post_results = []
    say_results = []
    pin_results = []
    repost_results = []
    luvlist_results = []
    read_checkin_results = []
    watch_checkin_results = []
    listen_checkin_results = []
    play_checkin_results = []

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
                read_checkin_results,
                watch_checkin_results,
                listen_checkin_results,
                play_checkin_results,
            ) = filter_write(query, search_terms, is_user_authenticated)

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

        if model in ["all", "entity"]:
            creator_results, company_results = filter_entity(query, search_terms)

        if model == "self":
            (
                post_results,
                say_results,
                pin_results,
                repost_results,
                luvlist_results,
                read_checkin_results,
                watch_checkin_results,
                listen_checkin_results,
                play_checkin_results,
            ) = filter_self(request.user, search_terms)

    execution_time = time.time() - start_time

    return render(
        request,
        "accounts/search_results.html",
        {
            "query": query,
            "model": model,
            "user_results": user_results,
            # entity
            "creator_results": creator_results,
            "company_results": company_results,
            # write
            "post_results": post_results,
            "say_results": say_results,
            "pin_results": pin_results,
            "repost_results": repost_results,
            "luvlist_results": luvlist_results,
            "read_checkin_results": read_checkin_results,
            "watch_checkin_results": watch_checkin_results,
            "listen_checkin_results": listen_checkin_results,
            "play_checkin_results": play_checkin_results,
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
    repost_ct = ContentType.objects.get_for_model(Repost)
    post_ct = ContentType.objects.get_for_model(Post)
    say_ct = ContentType.objects.get_for_model(Say)
    pin_ct = ContentType.objects.get_for_model(Pin)
    readcheckin_ct = ContentType.objects.get_for_model(ReadCheckIn)
    listencheckin_ct = ContentType.objects.get_for_model(ListenCheckIn)
    watchcheckin_ct = ContentType.objects.get_for_model(WatchCheckIn)
    gamecheckin_ct = ContentType.objects.get_for_model(PlayCheckIn)

    # Combine all content types into a list
    all_cts = [
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


##################
## App Password ##
##################


@login_required
def app_password_list(request, username):
    if request.method == "POST":
        form = AppPasswordForm(request.POST)
        if form.is_valid():
            app_password = form.save(commit=False)
            app_password.user = request.user
            app_password.save()
            messages.success(request, "App password created successfully.")
            return redirect("accounts:app_password", username=request.user.username)
    else:
        form = AppPasswordForm()

    passwords = AppPassword.objects.filter(user=request.user)
    return render(
        request, "accounts/app_password.html", {"passwords": passwords, "form": form}
    )


@login_required
def delete_app_password(request, username, pk):
    AppPassword.objects.filter(id=pk, user=request.user).delete()
    messages.success(request, "App password deleted successfully.")
    return redirect("accounts:app_password", username=request.user.username)


##################
## Crossposters ##
##################
@login_required
def manage_crossposters(request, username):
    try:
        bluesky_account = request.user.bluesky_account
    except BlueSkyAccount.DoesNotExist:
        bluesky_account = None

    try:
        mastodon_account = request.user.mastodon_account
    except MastodonAccount.DoesNotExist:
        mastodon_account = None

    if request.method == "POST":
        if "unlink_bluesky" in request.POST:
            if bluesky_account:
                bluesky_account.delete()
            return redirect("accounts:crossposters", username=request.user.username)

        if "unlink_mastodon" in request.POST:
            if mastodon_account:
                mastodon_account.delete()
            return redirect("accounts:crossposters", username=request.user.username)

        if "form_type" in request.POST and request.POST["form_type"] == "bluesky":
            form_bluesky = BlueSkyAccountForm(request.POST)
            if form_bluesky.is_valid():
                form_bluesky.save(request.user)
                return redirect("accounts:crossposters", username=request.user.username)

        if "form_type" in request.POST and request.POST["form_type"] == "mastodon":
            form_mastodon = MastodonAccountForm(request.POST)
            if form_mastodon.is_valid():
                form_mastodon.save(request.user)
                return redirect("accounts:crossposters", username=request.user.username)
    else:
        form_bluesky = BlueSkyAccountForm()
        form_mastodon = MastodonAccountForm()

    context = {
        "bluesky_account": bluesky_account,
        "mastodon_account": mastodon_account,
        "form_bluesky": form_bluesky,
        "form_mastodon": form_mastodon,
    }
    return render(request, "accounts/crossposters.html", context)


class ManageInvitationsView(View):
    def get(self, request, username):
        if request.user.username != username:
            return HttpResponseForbidden("You are not authorized to view this page.")

        user = request.user
        invitation_codes = user.codes_generated.order_by("-generated_at").all()

        # Get the date of the last code used or the user's join date if no code was used
        last_used_code = (
            user.codes_generated.filter(is_used=True).order_by("-generated_at").first()
        )
        last_relevant_date = (
            last_used_code.generated_at if last_used_code else user.date_joined
        )
        days_since_last_relevant = (timezone.now() - last_relevant_date).days

        # Calculate the number of elapsed TIME_RESTRICTION periods
        elapsed_periods = days_since_last_relevant // TIME_RESTRICTION

        # Determine the total number of codes the user is allowed to have at this point
        total_allowed_codes = min(elapsed_periods, 5)

        # Determine if the user can generate new codes
        current_unused_codes = user.codes_generated.filter(is_used=False).count()
        can_generate_new_code = total_allowed_codes > current_unused_codes

        # Determine the next date when new codes can be generated
        next_code_generation_info = ""
        if not can_generate_new_code:
            # Calculate the next code generation date
            next_generation_time = last_relevant_date + timedelta(
                days=(elapsed_periods + 1) * TIME_RESTRICTION
            )
            next_code_generation_date = next_generation_time.date()

            if current_unused_codes >= 5:
                next_code_generation_info = (
                    "You are holding the maximum number of invitation codes."
                )
            else:
                next_code_generation_info = (
                    f"Next code can be generated on {next_code_generation_date}."
                )

        context = {
            "invitation_codes": invitation_codes,
            "can_generate_new_code": can_generate_new_code,
            "next_code_generation_info": next_code_generation_info,
        }
        return render(request, "accounts/invitation_management.html", context)

    def post(self, request, username):
        if request.user.username != username:
            return HttpResponseForbidden("You are not authorized to view this page.")

        user = request.user

        # Get the date of the last code used or the user's join date if no code was used
        last_used_code = (
            user.codes_generated.filter(is_used=True).order_by("-generated_at").first()
        )
        last_relevant_date = (
            last_used_code.generated_at if last_used_code else user.date_joined
        )
        days_since_last_relevant = (timezone.now() - last_relevant_date).days

        # Calculate the number of elapsed TIME_RESTRICTION periods
        elapsed_periods = days_since_last_relevant // TIME_RESTRICTION

        # Determine the total number of codes the user is allowed to have at this point
        total_allowed_codes = min(elapsed_periods, 5)

        # Calculate the number of new codes that can be generated
        current_unused_codes = user.codes_generated.filter(is_used=False).count()
        new_codes_needed = total_allowed_codes - current_unused_codes

        if new_codes_needed > 0:
            # Generate new codes up to the calculated number
            for _ in range(new_codes_needed):
                InvitationCode.objects.create(
                    generated_by=user, generated_at=timezone.now()
                )

        return redirect("accounts:manage_invitations", username=username)


#################
## Deactivation #
#################


def deactivate_account(request, username):
    if request.method == "POST":
        user = request.user
        if (
            user.username == username
        ):  # Check if the username matches the logged-in user
            user.is_deactivated = True
            user.is_active = False
            user.deactivated_at = timezone.now()
            user.save()

            # Log the user out
            logout(request)

            # Render the success template
            return render(
                request,
                "accounts/account_deactivation_success.html",
                {"username": username},
            )

    return render(
        request, "accounts/account_deactivation_confirm.html", {"username": username}
    )


@receiver(pre_save, sender=CustomUser)
def handle_user_deactivation(sender, instance, **kwargs):
    if not instance.is_active:
        # Update related instances
        Say.objects.filter(user=instance).update(content="REMOVED")
        Post.objects.filter(user=instance).update(title="REMOVED", content="REMOVED")
        Pin.objects.filter(user=instance).update(
            title="REMOVED", content="REMOVED", url="http://removed.removed"
        )
        Repost.objects.filter(user=instance).update(content="REMOVED")
        Comment.objects.filter(user=instance).update(content="REMOVED")
        ReadCheckIn.objects.filter(user=instance).update(content="REMOVED")
        WatchCheckIn.objects.filter(user=instance).update(content="REMOVED")
        ListenCheckIn.objects.filter(user=instance).update(content="REMOVED")
        PlayCheckIn.objects.filter(user=instance).update(content="REMOVED")

        # Handle LuvList instances
        luvlists = LuvList.objects.filter(user=instance)
        for luvlist in luvlists:
            if luvlist.allow_collaboration:
                # Transfer ownership to the first collaborator
                collaborators = luvlist.collaborators.exclude(id=instance.id)
                if collaborators.exists():
                    new_owner = collaborators.first()
                    luvlist.user = new_owner
                    luvlist.collaborators.remove(instance)
                    luvlist.save()
                else:
                    # If no collaborators, treat as non-collaborative
                    luvlist.title = "REMOVED"
                    luvlist.save()
                    # Optionally remove items from the LuvList
                    ContentInList.objects.filter(
                        luv_list=luvlist
                    ).delete()  # Assuming you have a model for items in a LuvList
            else:
                # Non-collaborative LuvList
                luvlist.title = "REMOVED"
                luvlist.save()
                # Optionally remove items from the LuvList
                ContentInList.objects.filter(
                    luv_list=luvlist
                ).delete()  # Assuming you have a model for items in a LuvList

        with transaction.atomic():
            # Delete Follow relationships
            Follow.objects.filter(follower=instance).delete()
            Follow.objects.filter(followed=instance).delete()

            # Set a unique random username
            instance.username = generate_unique_username()


def generate_unique_username(length=10):
    import random
    import string

    while True:
        # Generate a random string of letters and digits
        username = "".join(
            random.choices(string.ascii_letters + string.digits, k=length)
        )

        # Check if the username already exists
        if not CustomUser.objects.filter(username=username).exists():
            return username


#################
## Webmentions ##
#################


@csrf_exempt
@require_http_methods(["POST"])
def webmention(request):
    source = request.POST.get("source")
    target = request.POST.get("target")

    if not source or not target:
        return HttpResponseBadRequest("Source and target must be provided.")

    # Check if the source and target are valid URLs
    if not is_valid_url(source) or not is_valid_url(target):
        return HttpResponseBadRequest("Source and target must be valid URLs.")

    # Check if the source is a like from Bridgy
    if "/like/" in source:
        return JsonResponse({"status": "refused", "message": "Likes are not accepted."})

    # Check if a WebMention with the same source and target already exists
    existing_webmention = WebMention.objects.filter(
        source=source, target=target
    ).first()
    if existing_webmention:
        return JsonResponse(
            {"status": "info", "message": "Duplicate WebMention ignored."}
        )

    verified = verify_webmention(source, target)

    if verified:
        webmention_data = fetch_webmention_data(source)

        # Check if webmention_data is not empty
        if webmention_data:
            # Create and save the WebMention instance
            webmention_instance = WebMention(
                source=source,
                target=target,
                verified=True,
                author_name=webmention_data.get("author_name"),
                author_url=webmention_data.get("author_url"),
                content_title=webmention_data.get("content_title"),
                content_url=webmention_data.get("content_url"),
                content=webmention_data.get("content"),
                mention_type=webmention_data.get("mention_type"),
            )
            webmention_instance.save()
            return JsonResponse(
                {"status": "success", "message": "WebMention received."}
            )
        else:
            return JsonResponse(
                {"status": "failure", "message": "Failed to fetch WebMention data."}
            )
    else:
        return JsonResponse(
            {"status": "failure", "message": "WebMention not verified."}
        )


def verify_webmention(source, target):
    """
    Verify the WebMention by ensuring the source page links to the target.
    """
    try:
        response = requests.get(source)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Check if the source page contains a link to the target URL
        for link in soup.find_all("a", href=True):
            if re.match(target, link["href"]):
                return True
        return False
    except requests.RequestException:
        return False


def is_valid_url(url):
    """
    Validate the URL by ensuring it is a valid URL and not blacklisted.
    """
    BLACKLISTED_URLS = []
    # # Check if the URL is blacklisted
    if url in BLACKLISTED_URLS:
        return False

    # Check if the URL is valid
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def fetch_webmention_data(source_url):
    try:
        response = requests.get(source_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Determine the type of WebMention
        mention_type = "other"
        if "/post/" in source_url:
            mention_type = "post"
        elif "/repost/" in source_url:
            mention_type = "repost"
        elif "/comment/" in source_url or soup.select_one(".e-content"):
            mention_type = "comment"

        # Extract data
        author_name = (
            soup.select_one(".p-author .p-name").get_text(strip=True)
            if soup.select_one(".p-author .p-name")
            else None
        )
        # Format the author URL if it matches the pattern
        author_url = (
            soup.select_one(".p-author .u-url")["href"]
            if soup.select_one(".p-author .u-url")
            else None
        )
        if author_url:
            match = re.search(r"https://(.+)/@(.+)", author_url)
            if match:
                author_url = f"@{match.group(2)}@{match.group(1)}"

        content = (
            soup.select_one(".e-content").get_text()
            if soup.select_one(".e-content")
            else None
        )
        content_title = (
            soup.select_one(".p-name").get_text()
            if soup.select_one(".p-name")
            else None
        )
        content_url = (
            soup.select_one(".u-url")["href"] if soup.select_one(".u-url") else None
        )

        data = {
            "author_name": author_name,
            "author_url": author_url,
            "content": content,
            "content_title": content_title,
            "content_url": content_url,
            "mention_type": mention_type,
        }

        return data
    except requests.RequestException:
        # Handle exceptions
        return {}


@login_required
def delete_webmention(request, webmention_id):
    webmention = get_object_or_404(WebMention, id=webmention_id)

    # Optional: Check if the request.user has permission to delete the WebMention
    if not request.user.has_perm("delete_webmention", webmention):
        return HttpResponseForbidden()

    webmention.delete()
    # Redirect back to the referring page
    referer_url = request.META.get("HTTP_REFERER")
    if referer_url:
        return HttpResponseRedirect(referer_url)
    else:
        return redirect("activity_feed:activity_feed")
