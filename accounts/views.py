import base64
import datetime
import json
import os
import re
import time
from base64 import urlsafe_b64decode
from datetime import timedelta

import cbor2
import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.db import transaction
from django.db.models import Count, Max, Min, OuterRef, Q, Subquery
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.http import (
    Http404,
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
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from django_ratelimit.decorators import ratelimit
from PIL import Image, ImageDraw, ImageFont
from webauthn import (
    base64url_to_bytes,
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    RegistrationCredential,
)

from accounts.models import BlacklistedDomain, CustomUser
from activity_feed.models import Activity, Block, Follow
from entity.models import Company, Creator
from listen.models import Audiobook, ListenCheckIn, Podcast, Release, Track
from listen.models import Work as MusicWork
from play.models import Game, PlayCheckIn
from play.models import Work as GameWork
from read.models import Book, BookSeries
from read.models import Instance as LitInstance
from read.models import Issue, Periodical, ReadCheckIn
from read.models import Work as LitWork
from visit.models import Location, VisitCheckIn
from watch.models import Episode, Movie, Series, WatchCheckIn
from write.models import Comment, ContentInList, LuvList, Pin, Post, Repost, Say, Tag
from write.utils_formatting import check_required_js

from .forms import (
    AppPasswordForm,
    BlueSkyAccountForm,
    CustomPasswordChangeForm,
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
    WebAuthnCredential,
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
    template_name = "registration/signup.html"

    def dispatch(self, request, *args, **kwargs):
        # Redirect to activity feed if user is already logged in
        if self.request.user.is_authenticated:
            return redirect(
                "activity_feed:activity_feed"
            )  # Replace 'activity_feed' with the correct URL name for your activity feed
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        self.object = form.save()
        login(self.request, self.object)
        self.request.session["is_first_login"] = True
        self.request.session.save()
        print(
            "Session is_first_login set: %s", self.request.session.get("is_first_login")
        )
        # set invitation code as used
        if self.object.code_used:  # Check if the user used a code
            self.object.code_used.is_used = True
            self.object.code_used.save()

        signup_method = form.cleaned_data.get("signup_method")
        if signup_method in ["passkey", "both"]:
            return redirect("signup_passkey")
        else:
            return redirect("activity_feed:activity_feed")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invite_code = self.request.GET.get("code")
        if invite_code:
            context["form"].fields["invitation_code"].initial = invite_code
            context["form"].fields["invitation_code"].widget.attrs["readonly"] = True
            context["form"].fields["invitation_code"].widget.attrs[
                "class"
            ] = "readonly-field"
            context["form"].fields["invitation_code"].help_text = ""
            invite_code = InvitationCode.objects.get(code=invite_code)
            context["inviter"] = invite_code.generated_by
            context["invite_code_used"] = invite_code.is_used
        return context


class CustomLoginView(LoginView):
    template_name = "registration/login.html"

    def dispatch(self, request, *args, **kwargs):
        # Redirect to activity feed if user is already logged in
        if self.request.user.is_authenticated:
            return redirect(
                "activity_feed:activity_feed"
            )  # Replace 'activity_feed' with the correct URL name for your activity feed
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["recent_books"] = Book.objects.order_by("-created_at")[:6]
        context["recent_movies"] = Movie.objects.order_by("-created_at")[:6]
        context["recent_series"] = Series.objects.order_by("-created_at")[:6]
        context["recent_music"] = Release.objects.order_by("-created_at")[:6]
        context["recent_games"] = Game.objects.order_by("-created_at")[:6]

        return context


class CustomPasswordChangeView(PasswordChangeView):
    form_class = CustomPasswordChangeForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        username = self.kwargs["username"]
        user = get_object_or_404(CustomUser, username=username)
        context["passkeys_exist"] = WebAuthnCredential.objects.filter(
            user=user
        ).exists()
        print(
            "Accessing session is_first_login:",
            self.request.session.get("is_first_login"),
        )
        context["is_first_login"] = self.request.session.get("is_first_login")
        return context

    def get_success_url(self):
        return reverse_lazy("activity_feed:activity_feed")


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
        latest_visit_checkins = get_latest_checkins(
            user=self.object, checkin_model=VisitCheckIn
        )

        visiting = latest_visit_checkins.filter(
            status__in=["visiting", "revisiting"]
        ).order_by("-timestamp")[:6]
        visited = latest_visit_checkins.filter(
            status__in=["visited", "revisited"]
        ).order_by("-timestamp")[:6]
        living_in = latest_visit_checkins.filter(status__in=["living-here"]).order_by(
            "-timestamp"
        )[:6]

        context["visiting"] = visiting
        context["visited"] = visited
        context["living_in"] = living_in
        context["does_visit_exist"] = does_visit_exist = (
            visited.exists() or visiting.exists()
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
        context["feed_user"] = user = User.objects.get(username=username)

        # Add the flags to the context
        include_mathjax, include_mermaid = check_required_js(context["page_obj"])
        context["include_mathjax"] = include_mathjax
        context["include_mermaid"] = include_mermaid

        latest_visit_checkins = get_latest_checkins(
            user=user, checkin_model=VisitCheckIn
        )
        living_in = latest_visit_checkins.filter(status__in=["living-here"]).order_by(
            "-timestamp"
        )[:1]
        context["living_in"] = living_in

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
    response["Content-Disposition"] = (
        f'attachment; filename="{request.user.username}_data.json"'
    )

    return response


class RequestInvitationView(View):
    def post(self, request):
        email = request.POST.get("email")
        if email:
            # Extract the domain from the email address
            domain = email.split("@")[-1]

            # Check if the domain is blacklisted
            if BlacklistedDomain.objects.filter(domain=domain).exists():
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
        elif "blacklist_email_id" in request.POST:
            # New logic to blacklist a domain
            invitation_request = InvitationRequest.objects.get(
                id=request.POST.get("blacklist_email_id")
            )
            domain = invitation_request.email.split("@")[-1]
            BlacklistedDomain.objects.get_or_create(domain=domain)
            # Optionally, delete all requests from this domain or mark them as handled
            InvitationRequest.objects.filter(email__endswith=domain).delete()
            return HttpResponseRedirect(reverse("manage_invitation_requests"))

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
            .annotate(
                annotated_earliest_release_date=Min(
                    "region_release_dates__release_date"
                )
            )
            .order_by("annotated_earliest_release_date")
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
            .annotate(annotated_release_date=Min("region_release_dates__release_date"))
            .order_by("annotated_release_date")
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


def filter_location(query, search_terms):
    location_results = Location.objects.all()

    for term in search_terms:
        location_results = (
            location_results.filter(
                Q(name__icontains=term) | Q(other_names__icontains=term)
            )
            .distinct()
            .order_by("name")
        )

    return location_results


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
    # visit
    location_results = []

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

        if model in ["all", "visit"]:
            location_results = filter_location(query, search_terms)

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
            # location
            "location_results": location_results,
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


############################
## QR code for Invitations #
############################


def generate_qr_code(request, username, invite_code):
    # Create QR code with the invitation link
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=5,
    )
    qr.add_data(f'{request.build_absolute_uri("/signup/")}?code={invite_code}')
    qr.make(fit=True)

    img = qr.make_image(fill_color="#eee", back_color="#4696fd")

    # Define additional space at the bottom
    additional_bottom_space = 80

    # Create a new image with additional space at the bottom
    new_width = img.size[0]
    new_height = img.size[1] + additional_bottom_space
    new_img = Image.new("RGB", (new_width, new_height), "#4696fd")
    new_img.paste(img, (0, 0))  # Paste the QR code at the top of the new image

    I1 = ImageDraw.Draw(new_img)

    # Load fonts
    font_path = os.path.join(
        settings.BASE_DIR, "static", "luvdb", "fonts", "NotoSans.ttf"
    )
    font = ImageFont.truetype(font_path, 105)

    # Add logo text at the bottom
    text = "LʌvDB"
    text_width = I1.textlength(text, font=font)
    x = (new_width - text_width) // 2
    y = img.size[1] + (additional_bottom_space - 200) // 2
    I1.text((x, y), text, fill="#eee", font=font)

    # Create HTTP response
    response = HttpResponse(content_type="image/png")
    new_img.save(response, "PNG")
    return response


##################
# Year in Review #
##################


class YearInReviewView(DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"
    template_name = "accounts/year_in_review.html"

    def dispatch(self, request, *args, **kwargs):
        # Get the User object
        profile_user = get_object_or_404(
            get_user_model(), username=self.kwargs["username"]
        )

        # If the user's profile isn't public and the current user isn't authenticated, raise a 404 error
        if not profile_user.is_public and not request.user.is_authenticated:
            return redirect("{}?next={}".format(reverse("login"), request.path))

        # Otherwise, proceed as normal
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object
        current_year = timezone.now().year
        requested_year = self.kwargs.get("year", current_year)

        # Check if the current year's stats are available
        is_data_available = (
            requested_year <= current_year
            and timezone.now().date() > datetime.date(requested_year, 12, 25)
        )

        if is_data_available:
            context["if_data_available"] = True
            yearly_stats = self.get_yearly_stats(user, requested_year)
            context.update(yearly_stats)
        else:
            context["if_data_available"] = False

        context["requested_year"] = requested_year
        # Add previous and next year for navigation, considering access control
        context["all_years"] = range(2023, current_year + 1)
        context["user"] = user

        return context

    def get_yearly_stats(self, user, year):
        start_date = datetime.date(year, 1, 1)
        end_date = datetime.date(year + 1, 1, 1)

        yearly_activities = Activity.objects.filter(
            user=user, timestamp__range=(start_date, end_date)
        ).count()

        # writing
        ## posts
        posts = Post.objects.filter(
            user=user, timestamp__range=(start_date, end_date)
        ).count()
        ## says / reposts
        says = Say.objects.filter(
            user=user, timestamp__range=(start_date, end_date)
        ).count()
        reposts = Repost.objects.filter(
            user=user, timestamp__range=(start_date, end_date)
        ).count()
        ## pins
        pins = Pin.objects.filter(
            user=user, timestamp__range=(start_date, end_date)
        ).count()
        ## comments
        comments = Comment.objects.filter(
            user=user, timestamp__range=(start_date, end_date)
        ).count()
        ## luvlists
        luvlists = LuvList.objects.filter(
            user=user, timestamp__range=(start_date, end_date)
        ).count()
        luvlists_personal = LuvList.objects.filter(
            user=user,
            timestamp__range=(start_date, end_date),
            allow_collaboration=False,
        ).count()
        luvlists_collab = LuvList.objects.filter(
            collaborators=user,
            updated_at__range=(start_date, end_date),
            allow_collaboration=True,
        ).count()

        total_writing = posts + says + reposts + pins + comments

        # checkins
        ## read
        read_checkins = ReadCheckIn.objects.filter(
            user=user, timestamp__range=(start_date, end_date)
        ).count()
        books_checked_in = (
            ReadCheckIn.objects.filter(
                user=user,
                content_type=ContentType.objects.get(app_label="read", model="book"),
                timestamp__range=(start_date, end_date),
            )
            .values("object_id")
            .distinct()
            .count()
        )
        books_to_read = count_media_with_latest_status(
            ReadCheckIn, "read", "book", user, year, "to_read"
        )
        books_reading = count_media_with_latest_status(
            ReadCheckIn, "read", "book", user, year, "reading"
        )
        books_rereading = count_media_with_latest_status(
            ReadCheckIn, "read", "book", user, year, "rereading"
        )
        books_read = count_media_with_latest_status(
            ReadCheckIn, "read", "book", user, year, "finished_reading"
        )
        books_reread = count_media_with_latest_status(
            ReadCheckIn, "read", "book", user, year, "reread"
        )
        books_sampled = count_media_with_latest_status(
            ReadCheckIn, "read", "book", user, year, "sampled"
        )
        books_paused = count_media_with_latest_status(
            ReadCheckIn, "read", "book", user, year, "paused"
        )
        books_abandoned = count_media_with_latest_status(
            ReadCheckIn, "read", "book", user, year, "abandoned"
        )
        books_afterthought = count_media_with_latest_status(
            ReadCheckIn, "read", "book", user, year, "afterthought"
        )

        issues_checked_in = (
            ReadCheckIn.objects.filter(
                user=user,
                content_type=ContentType.objects.get(app_label="read", model="issue"),
                timestamp__range=(start_date, end_date),
            )
            .values("object_id")
            .distinct()
            .count()
        )
        issues_to_read = count_media_with_latest_status(
            ReadCheckIn, "read", "issue", user, year, "to_read"
        )
        issues_reading = count_media_with_latest_status(
            ReadCheckIn, "read", "issue", user, year, "reading"
        )
        issues_rereading = count_media_with_latest_status(
            ReadCheckIn, "read", "issue", user, year, "rereading"
        )
        issues_read = count_media_with_latest_status(
            ReadCheckIn, "read", "issue", user, year, "finished_reading"
        )
        issues_reread = count_media_with_latest_status(
            ReadCheckIn, "read", "issue", user, year, "reread"
        )
        issues_sampled = count_media_with_latest_status(
            ReadCheckIn, "read", "issue", user, year, "sampled"
        )
        issues_paused = count_media_with_latest_status(
            ReadCheckIn, "read", "issue", user, year, "paused"
        )
        issues_abandoned = count_media_with_latest_status(
            ReadCheckIn, "read", "issue", user, year, "abandoned"
        )
        issues_afterthought = count_media_with_latest_status(
            ReadCheckIn, "read", "issue", user, year, "afterthought"
        )

        ## watch
        watch_checkins = WatchCheckIn.objects.filter(
            user=user, timestamp__range=(start_date, end_date)
        ).count()
        # Get the ContentType for the Book model (or any other model you're interested in)
        movies_checked_in = (
            WatchCheckIn.objects.filter(
                user=user,
                content_type=ContentType.objects.get(app_label="watch", model="movie"),
                timestamp__range=(start_date, end_date),
            )
            .values("object_id")
            .distinct()
            .count()
        )
        movies_to_watch = count_media_with_latest_status(
            WatchCheckIn, "watch", "movie", user, year, "to_watch"
        )
        movies_watching = count_media_with_latest_status(
            WatchCheckIn, "watch", "movie", user, year, "watching"
        )
        movies_rewatching = count_media_with_latest_status(
            WatchCheckIn, "watch", "movie", user, year, "rewatching"
        )
        movies_watched = count_media_with_latest_status(
            WatchCheckIn, "watch", "movie", user, year, "watched"
        )
        movies_rewatched = count_media_with_latest_status(
            WatchCheckIn, "watch", "movie", user, year, "rewatched"
        )
        movies_paused = count_media_with_latest_status(
            WatchCheckIn, "watch", "movie", user, year, "paused"
        )
        movies_abandoned = count_media_with_latest_status(
            WatchCheckIn, "watch", "movie", user, year, "abandoned"
        )
        series_checked_in = (
            WatchCheckIn.objects.filter(
                user=user,
                content_type=ContentType.objects.get(app_label="watch", model="series"),
                timestamp__range=(start_date, end_date),
            )
            .values("object_id")
            .distinct()
            .count()
        )
        series_to_watch = count_media_with_latest_status(
            WatchCheckIn, "watch", "series", user, year, "to_watch"
        )
        series_watching = count_media_with_latest_status(
            WatchCheckIn, "watch", "series", user, year, "watching"
        )
        series_rewatching = count_media_with_latest_status(
            WatchCheckIn, "watch", "series", user, year, "rewatching"
        )
        series_watched = count_media_with_latest_status(
            WatchCheckIn, "watch", "series", user, year, "watched"
        )
        series_rewatched = count_media_with_latest_status(
            WatchCheckIn, "watch", "series", user, year, "rewatched"
        )
        series_paused = count_media_with_latest_status(
            WatchCheckIn, "watch", "series", user, year, "paused"
        )
        series_abandoned = count_media_with_latest_status(
            WatchCheckIn, "watch", "series", user, year, "abandoned"
        )

        ## listen
        listen_checkins = ListenCheckIn.objects.filter(
            user=user, timestamp__range=(start_date, end_date)
        ).count()
        ### Release
        releases_checked_in = (
            ListenCheckIn.objects.filter(
                user=user,
                content_type=ContentType.objects.get(
                    app_label="listen", model="release"
                ),
                timestamp__range=(start_date, end_date),
            )
            .values("object_id")
            .distinct()
            .count()
        )
        releases_to_listen = count_media_with_latest_status(
            ListenCheckIn, "listen", "release", user, year, "to_listen"
        )
        releases_looping = count_media_with_latest_status(
            ListenCheckIn, "listen", "release", user, year, "looping"
        )
        releases_listened = count_media_with_latest_status(
            ListenCheckIn, "listen", "release", user, year, "listened"
        )
        releases_relistened = count_media_with_latest_status(
            ListenCheckIn, "listen", "release", user, year, "relistened"
        )
        releases_abandoned = count_media_with_latest_status(
            ListenCheckIn, "listen", "release", user, year, "abandoned"
        )
        ### Podcast
        podcasts_checked_in = (
            ListenCheckIn.objects.filter(
                user=user,
                content_type=ContentType.objects.get(
                    app_label="listen", model="podcast"
                ),
                timestamp__range=(start_date, end_date),
            )
            .values("object_id")
            .distinct()
            .count()
        )
        podcasts_to_listen = count_media_with_latest_status(
            ListenCheckIn, "listen", "podcast", user, year, "to_listen"
        )
        podcasts_subscribed = count_media_with_latest_status(
            ListenCheckIn, "listen", "podcast", user, year, "subscribed"
        )
        podcasts_unsubscribed = count_media_with_latest_status(
            ListenCheckIn, "listen", "podcast", user, year, "unsubscribed"
        )
        podcasts_sampled = count_media_with_latest_status(
            ListenCheckIn, "listen", "podcast", user, year, "sampled"
        )
        ### Audiobook
        audiobooks_checked_in = (
            ListenCheckIn.objects.filter(
                user=user,
                content_type=ContentType.objects.get(
                    app_label="listen", model="audiobook"
                ),
                timestamp__range=(start_date, end_date),
            )
            .values("object_id")
            .distinct()
            .count()
        )
        audiobooks_to_listen = count_media_with_latest_status(
            ListenCheckIn, "listen", "audiobook", user, year, "to_listen"
        )
        audiobooks_listening = count_media_with_latest_status(
            ListenCheckIn, "listen", "audiobook", user, year, "listening"
        )
        audiobooks_relistening = count_media_with_latest_status(
            ListenCheckIn, "listen", "audiobook", user, year, "relistening"
        )
        audiobooks_listened = count_media_with_latest_status(
            ListenCheckIn, "listen", "audiobook", user, year, "listened"
        )
        audiobooks_relistened = count_media_with_latest_status(
            ListenCheckIn, "listen", "audiobook", user, year, "relistened"
        )
        audiobooks_paused = count_media_with_latest_status(
            ListenCheckIn, "listen", "audiobook", user, year, "paused"
        )
        audiobooks_abandoned = count_media_with_latest_status(
            ListenCheckIn, "listen", "audiobook", user, year, "abandoned"
        )
        ## play
        play_checkins = PlayCheckIn.objects.filter(
            user=user, timestamp__range=(start_date, end_date)
        ).count()
        games_checked_in = (
            PlayCheckIn.objects.filter(
                user=user,
                content_type=ContentType.objects.get(app_label="play", model="game"),
                timestamp__range=(start_date, end_date),
            )
            .values("object_id")
            .distinct()
            .count()
        )
        games_to_play = count_media_with_latest_status(
            PlayCheckIn, "play", "game", user, year, "to_play"
        )
        games_playing = count_media_with_latest_status(
            PlayCheckIn, "play", "game", user, year, "playing"
        )
        games_replaying = count_media_with_latest_status(
            PlayCheckIn, "play", "game", user, year, "replaying"
        )
        games_played = count_media_with_latest_status(
            PlayCheckIn, "play", "game", user, year, "played"
        )
        games_replayed = count_media_with_latest_status(
            PlayCheckIn, "play", "game", user, year, "replayed"
        )
        games_paused = count_media_with_latest_status(
            PlayCheckIn, "play", "game", user, year, "paused"
        )
        games_abandoned = count_media_with_latest_status(
            PlayCheckIn, "play", "game", user, year, "abandoned"
        )

        ## total checkins
        total_checkins = (
            read_checkins + watch_checkins + listen_checkins + play_checkins
        )

        # contributions
        ## Read
        contributed_litworks = LitWork.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()
        contributed_litinstances = LitInstance.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()
        contributed_books = Book.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()
        contributed_periodicals = Periodical.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()
        contributed_issues = Issue.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()

        ## watch
        contributed_movies = Movie.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()
        contributed_series = Series.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()
        contributed_episodes = Episode.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()
        ## listen
        contributed_musicworks = MusicWork.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()
        contributed_tracks = Track.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()
        contributed_releases = Release.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()
        contributed_audiobooks = Audiobook.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()
        ## play
        contributed_gameworks = GameWork.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()
        contributed_games = Game.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()

        # entity
        contributed_creators = Creator.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()
        contributed_companies = Company.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()

        # location
        contributed_locations = Location.objects.filter(
            created_by=user, created_at__range=(start_date, end_date)
        ).count()

        total_contribution = (
            contributed_litworks
            + contributed_litinstances
            + contributed_books
            + contributed_periodicals
            + contributed_issues
            + contributed_movies
            + contributed_series
            + contributed_episodes
            + contributed_musicworks
            + contributed_tracks
            + contributed_releases
            + contributed_gameworks
            + contributed_games
            + contributed_creators
            + contributed_companies
            + contributed_locations
        )
        # Similarly for other models like ReadCheckIn, ListenCheckIn, etc.

        return {
            "yearly_activities": yearly_activities,
            # writing
            "total_writing": total_writing,
            "posts": posts,
            "says": says,
            "reposts": reposts,
            "pins": pins,
            "comments": comments,
            "luvlists": luvlists,
            "luvlists_personal": luvlists_personal,
            "luvlists_collab": luvlists_collab,
            # checkins
            "total_checkins": total_checkins,
            "read_checkins": read_checkins,
            "watch_checkins": watch_checkins,
            "listen_checkins": listen_checkins,
            "play_checkins": play_checkins,
            ## read checkins breakdown
            ### Book
            "books_checked_in": books_checked_in,
            "books_to_read": books_to_read,
            "books_reading": books_reading,
            "books_rereading": books_rereading,
            "books_read": books_read,
            "books_reread": books_reread,
            "books_sampled": books_sampled,
            "books_paused": books_paused,
            "books_abandoned": books_abandoned,
            "books_afterthought": books_afterthought,
            ### Issue
            "issues_checked_in": issues_checked_in,
            "issues_to_read": issues_to_read,
            "issues_reading": issues_reading,
            "issues_rereading": issues_rereading,
            "issues_read": issues_read,
            "issues_reread": issues_reread,
            "issues_sampled": issues_sampled,
            "issues_paused": issues_paused,
            "issues_abandoned": issues_abandoned,
            "issues_afterthought": issues_afterthought,
            ## Watch checkins breakdown
            ### Movie
            "movies_checked_in": movies_checked_in,
            "movies_to_watch": movies_to_watch,
            "movies_watching": movies_watching,
            "movies_rewatching": movies_rewatching,
            "movies_watched": movies_watched,
            "movies_rewatched": movies_rewatched,
            "movies_paused": movies_paused,
            "movies_abandoned": movies_abandoned,
            ### Series
            "series_checked_in": series_checked_in,
            "series_to_watch": series_to_watch,
            "series_watching": series_watching,
            "series_rewatching": series_rewatching,
            "series_watched": series_watched,
            "series_rewatched": series_rewatched,
            "series_paused": series_paused,
            "series_abandoned": series_abandoned,
            ## listen checkins breakdown
            ### releases
            "releases_checked_in": releases_checked_in,
            "releases_to_listen": releases_to_listen,
            "releases_looping": releases_looping,
            "releases_listened": releases_listened,
            "releases_relistened": releases_relistened,
            "releases_abandoned": releases_abandoned,
            ### podcasts
            "podcasts_checked_in": podcasts_checked_in,
            "podcasts_to_listen": podcasts_to_listen,
            "podcasts_subscribed": podcasts_subscribed,
            "podcasts_unsubscribed": podcasts_unsubscribed,
            "podcasts_sampled": podcasts_sampled,
            ### audiobooks
            "audiobooks_checked_in": audiobooks_checked_in,
            "audiobooks_to_listen": audiobooks_to_listen,
            "audiobooks_listening": audiobooks_listening,
            "audiobooks_relistening": audiobooks_relistening,
            "audiobooks_listened": audiobooks_listened,
            "audiobooks_relistened": audiobooks_relistened,
            "audiobooks_paused": audiobooks_paused,
            "audiobooks_abandoned": audiobooks_abandoned,
            ## play checkins breakdown
            "games_checked_in": games_checked_in,
            "games_to_play": games_to_play,
            "games_playing": games_playing,
            "games_replaying": games_replaying,
            "games_played": games_played,
            "games_replayed": games_replayed,
            "games_paused": games_paused,
            "games_abandoned": games_abandoned,
            # contributions
            "total_contribution": total_contribution,
            "contributed_litworks": contributed_litworks,
            "contributed_litinstances": contributed_litinstances,
            "contributed_books": contributed_books,
            "contributed_periodicals": contributed_periodicals,
            "contributed_issues": contributed_issues,
            "contributed_movies": contributed_movies,
            "contributed_series": contributed_series,
            "contributed_episodes": contributed_episodes,
            "contributed_musicworks": contributed_musicworks,
            "contributed_tracks": contributed_tracks,
            "contributed_releases": contributed_releases,
            "contributed_audiobooks": contributed_audiobooks,
            "contributed_gameworks": contributed_gameworks,
            "contributed_games": contributed_games,
            "contributed_creators": contributed_creators,
            "contributed_companies": contributed_companies,
            "contributed_locations": contributed_locations,
            # other stats
        }


def count_media_with_latest_status(checkin_model, app_label, model, user, year, status):
    start_date = datetime.date(year, 1, 1)
    end_date = datetime.date(year, 12, 31)
    content_type = ContentType.objects.get(app_label=app_label, model=model)

    # Step 1: Get the latest check-in for each book
    latest_checkins = (
        checkin_model.objects.filter(
            user=user,
            content_type=content_type,
            timestamp__range=(start_date, end_date),
        )
        .values("object_id")
        .annotate(latest_checkin=Max("timestamp"))
    )

    # Step 2: Count the books with the specified status in their latest check-in
    count = (
        checkin_model.objects.filter(
            user=user,
            content_type=content_type,
            status=status,
            timestamp__range=(start_date, end_date),
        )
        .filter(
            # Match the latest check-in timestamp for each book
            Q(object_id__in=latest_checkins.values("object_id"))
            & Q(timestamp__in=latest_checkins.values("latest_checkin"))
        )
        .count()
    )

    return count


@login_required
def generate_registration_view(request):
    # Replace these with actual values appropriate for your application
    rp_id = settings.WEBAUTHN_RP_ID
    rp_name = settings.WEBAUTHN_RP_NAME
    user_id = str(request.user.id).encode()  # WebAuthn expects user ID to be a string
    user_name = request.user.username

    registration_options = generate_registration_options(
        rp_id=rp_id,
        rp_name=rp_name,
        user_id=user_id,
        user_name=user_name,
        attestation=AttestationConveyancePreference.DIRECT,
    )

    # Convert options to JSON for transmission to the client
    options_json = options_to_json(registration_options)

    try:
        import base64

        # Store the challenge in the session for later verification
        challenge_base64 = base64.urlsafe_b64encode(
            registration_options.challenge
        ).decode("utf-8")
        # Store the Base64-encoded challenge in the session
        request.session["webauthn_challenge"] = challenge_base64
    except Exception as e:
        print(f"Error storing challenge: {str(e)}")

    return JsonResponse(options_json, safe=False)


@login_required
def verify_registration_view(request):
    # Parse the incoming JSON data from the request body
    data = json.loads(request.body.decode("utf-8"))

    # Reconstructing the credential object similar to the py_webauthn example
    credential = {
        "id": data["id"],
        "rawId": data["rawId"],
        "response": {
            "attestationObject": data["response"]["attestationObject"],
            "clientDataJSON": data["response"]["clientDataJSON"],
        },
        "type": data["type"],
    }

    try:
        # Verify the registration response
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(
                request.session.pop("webauthn_challenge")
            ),
            expected_origin=settings.ROOT_URL,
            expected_rp_id=settings.WEBAUTHN_RP_ID,
        )

        credential_id = base64.urlsafe_b64encode(base64url_to_bytes(data["id"])).decode(
            "utf-8"
        )
        public_key = base64.urlsafe_b64encode(
            verification.credential_public_key
        ).decode("utf-8")

        # Decode the attestationObject to extract the AAGUID
        attestation_object_b64 = data["response"]["attestationObject"]

        attestation_object = cbor2.loads(
            base64.urlsafe_b64decode(attestation_object_b64 + "==")
        )
        auth_data = attestation_object.get("authData")
        aaguid = auth_data[37:53].hex()

        existing_credential = WebAuthnCredential.objects.filter(
            user=request.user, aaguid=aaguid
        ).first()

        if existing_credential:
            # If the credential exists, update it instead of creating a new one
            existing_credential.credential_id = credential_id
            existing_credential.public_key = public_key
            existing_credential.sign_count = verification.sign_count
            existing_credential.save()
            return HttpResponse("Credential updated successfully")
        else:
            # Here, save the verified credential to your database
            WebAuthnCredential.objects.create(
                user=request.user,
                credential_id=credential_id,
                public_key=public_key,
                sign_count=verification.sign_count,
                key_name="Default Passkey Name",
                aaguid=aaguid,
            )
            return HttpResponse("Registration successful")

    except Exception as e:
        print(f"Verification failed: {str(e)}")  # Log the error
        return HttpResponseBadRequest(f"Verification failed: {str(e)}")


def generate_authentication_view(request):
    # Generate simple or complex options as needed. Example with simple options:
    authentication_options = generate_authentication_options(
        rp_id=settings.WEBAUTHN_RP_ID
    )

    # For complex scenarios, customize the call to generate_authentication_options as needed

    # Convert options to JSON for transmission to the client
    options_json = options_to_json(authentication_options)

    try:
        import base64

        # Store the challenge in the session for later verification
        challenge_base64 = base64.urlsafe_b64encode(
            authentication_options.challenge
        ).decode("utf-8")
        request.session["webauthn_challenge"] = challenge_base64
    except Exception as e:
        print(f"Error storing challenge: {str(e)}")

    return JsonResponse(options_json, safe=False)


def verify_authentication_view(request):
    # Parse the incoming JSON data from the request body
    data = json.loads(request.body.decode("utf-8"))

    # Reconstructing the credential object
    credential = {
        "id": data["id"],
        "rawId": data["rawId"],
        "response": {
            "authenticatorData": data["response"]["authenticatorData"],
            "clientDataJSON": data["response"]["clientDataJSON"],
            "signature": data["response"]["signature"],
            "userHandle": data["response"].get("userHandle", ""),
        },
        "type": data["type"],
    }

    try:
        credential_id = base64.urlsafe_b64encode(base64url_to_bytes(data["id"])).decode(
            "utf-8"
        )

        # Fetch the WebAuthnCredential object based on credential_id
        webauthn_credential = WebAuthnCredential.objects.get(
            credential_id=credential_id
        )

        # Verify the authentication response
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(
                request.session.pop("webauthn_challenge")
            ),
            expected_origin=settings.ROOT_URL,
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            credential_public_key=base64url_to_bytes(webauthn_credential.public_key),
            credential_current_sign_count=webauthn_credential.sign_count,
            require_user_verification=True,
        )

        # Update the sign_count in the database with the new sign_count from the verification
        webauthn_credential.sign_count = verification.new_sign_count
        webauthn_credential.last_used_at = timezone.now()
        webauthn_credential.save()

        # Authenticate the user in your system based on the successful verification
        user = webauthn_credential.user
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        return HttpResponse("Authentication successful")

    except WebAuthnCredential.DoesNotExist:
        return HttpResponseBadRequest("Credential not found.")
    except Exception as e:
        print(f"Authentication failed: {str(e)}")  # Log the error
        return HttpResponseBadRequest(f"Authentication failed: {str(e)}")


@login_required
def passkeys_view(request, username):
    # Fetch all WebAuthn credentials associated with the current user
    credentials = WebAuthnCredential.objects.filter(user=request.user)

    # Render the passkeys.html template, passing the credentials to the template
    return render(request, "accounts/passkeys.html", {"credentials": credentials})


@login_required
def edit_passkey(request, username, pk):
    # Fetch the WebAuthn credential to be edited, ensuring it belongs to the current user
    credential = get_object_or_404(WebAuthnCredential, pk=pk, user=request.user)

    if request.method == "POST":
        # Process the form submission
        key_name = request.POST.get("key_name", "").strip()
        if key_name:
            credential.key_name = key_name
            credential.save()
            messages.success(request, "Passkey name updated successfully.")
            return redirect("accounts:passkeys", username=request.user.username)
        else:
            messages.error(request, "Invalid passkey name.")

    return render(request, "accounts/passkey_edit.html", {"credential": credential})

    # For GET requests or if the form submission is invalid
    # return redirect("accounts:passkeys", username=username)


@login_required
def delete_passkey(request, username, pk):
    # Fetch the WebAuthn credential to be deleted
    credential = get_object_or_404(WebAuthnCredential, pk=pk)

    # Check if the credential belongs to the current user
    if credential.user != request.user:
        return HttpResponseForbidden("You are not authorized to delete this passkey.")

    # Delete the credential
    credential.delete()

    return redirect("accounts:passkeys", username=username)


@login_required
def signup_passkey(request):
    return render(request, "registration/signup_passkey.html")
