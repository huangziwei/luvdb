from collections import defaultdict

from dal import autocomplete
from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, F, Min, Q
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django_ratelimit.decorators import ratelimit

from listen.models import Audiobook, Release, ReleaseRole, Track, TrackRole
from listen.models import Work as ListenWork
from listen.models import WorkRole as ListenWorkRole
from play.models import Game, GameRole
from play.models import Work as PlayWork
from read.models import Book, BookRole
from read.models import Instance as ReadInstance
from read.models import Work as ReadWork
from scrape.wikipedia import scrape_company, scrape_creator
from visit.models import Location
from watch.models import Episode, EpisodeRole, Movie, MovieRole, Series, SeriesRole

from .forms import (
    CompanyForm,
    CompanyParentFormSet,
    CompanyPastNameFormSet,
    CreatorForm,
    MemberOfFormSet,
)
from .models import Company, Creator, Role


# helpers
def get_location_labels(location):
    if not location:
        return ""

    if location.level == Location.LEVEL0 or location.level == Location.LEVEL1:
        return f"{location.name}"
    elif location.level == Location.LEVEL4:
        return f"{location.name}, {location.parent.parent.name}"
    elif location.level == Location.LEVEL5:
        return f"{location.name}, {location.parent.parent.parent.name}"
    else:
        return f"{location.name}, {location.parent.name}"


# Create your views here.
class CreatorCreateView(LoginRequiredMixin, CreateView):
    model = Creator
    form_class = CreatorForm
    template_name = "entity/creator_create.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["memberof"] = MemberOfFormSet(self.request.POST, instance=self.object)
        else:
            data["memberof"] = MemberOfFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        memberof = context["memberof"]
        if not all(memberof_form.is_valid() for memberof_form in memberof):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if memberof.is_valid():
                memberof.instance = self.object
                memberof.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("entity:creator_detail", kwargs={"pk": self.object.pk})

    def post(self, request, *args, **kwargs):
        if "wiki_url" in request.POST:
            wiki_url = request.POST.get("wiki_url")
            data = scrape_creator(wiki_url)
            form = self.form_class(initial=data)
            memberof = MemberOfFormSet()
            return render(
                request, self.template_name, {"form": form, "memberof": memberof}
            )
        else:
            return super().post(request, *args, **kwargs)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class CreatorDetailView(DetailView):
    model = Creator
    template_name = "entity/creator_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        creator = self.object

        # read
        # Helper function to sort and group books
        def get_books_by_role(role, creator):
            from collections import defaultdict

            final_dict = defaultdict(list)
            processed_instances = set()
            processed_groups = set()

            books = Book.objects.filter(
                bookrole__role__name=role, bookrole__creator=creator
            ).distinct()

            for book in books:
                book_language = book.language or "Unknown"
                instances = ReadInstance.objects.filter(books=book)

                if not instances.exists() or instances.count() > 1:
                    if not book.book_group.exists():
                        final_dict[book_language].append(book)
                    else:
                        group = book.book_group.first()
                        if group.id not in processed_groups:
                            processed_groups.add(group.id)
                            first_published_book = group.books.order_by(
                                "publication_date"
                            ).first()
                            final_dict[book_language].append(first_published_book)
                else:
                    instance = instances.first()
                    if instance.id not in processed_instances:
                        processed_instances.add(instance.id)
                        final_dict[instance.language or "Unknown"].append(instance)

            for language in final_dict:
                final_dict[language].sort(
                    key=lambda x: getattr(x, "publication_date", None)
                )

            sorted_final_list = sorted(
                final_dict.items(), key=lambda x: len(x[1]), reverse=True
            )

            return dict(sorted_final_list)

        book_roles = (
            BookRole.objects.values_list("role__name", flat=True)
            .distinct()
            .order_by("role__name")
        )
        books = {}

        for role in book_roles:
            # Using a display-friendly format for the role in the keys
            formatted_role = f"As {role}"
            books_by_role = get_books_by_role(role, creator)
            if books_by_role:
                books[formatted_role] = books_by_role

        context["books"] = books

        work_roles = ["Author", "Illustrator", "Ghostwriter"]

        context["lit_works_all"] = (
            ReadWork.objects.filter(
                workrole__role__name__in=work_roles, workrole__creator=creator
            )
            .distinct()
            .order_by("publication_date")
        )

        work_types = ReadWork.WORK_TYPES
        lit_works = {}
        for work_type in work_types:
            lit_works[f"{work_type[1]}".replace(" ", "-").lower()] = (
                ReadWork.objects.filter(
                    workrole__role__name__in=work_roles,
                    workrole__creator=creator,
                    work_type=work_type[0],
                )
                .distinct()
                .order_by("publication_date")
            )
        context["lit_works"] = lit_works

        context["litworks_count"] = creator.read_works.distinct().count()
        context["litinstances_count"] = (
            ReadInstance.objects.filter(instancerole__creator=creator)
            .distinct()
            .count()
        )
        context["books_count"] = (
            Book.objects.filter(bookrole__creator=creator).distinct().count()
        )

        # listen
        roles_as_performer = [
            "Conductor",
            "Performer",
        ]

        def get_releases_by_type_and_group(releases):
            # Group the releases by their ReleaseGroup and sort them by release_date within each group
            release_by_group = {}
            for release in releases:
                group = (
                    release.release_group.first()
                )  # Assuming a release can only belong to one group
                if group:
                    release_by_group.setdefault(group, []).append(release)

            for group, group_releases in release_by_group.items():
                # Get the earliest release date for each group
                release_by_group[group] = sorted(
                    group_releases, key=lambda r: r.release_date
                )[0]

            # For releases that do not belong to any group, treat them as individual "groups"
            individual_releases = [r for r in releases if not r.release_group.exists()]
            for release in individual_releases:
                release_by_group[release] = (
                    release  # Individual releases are their own "group"
                )

            # Sort the final release list by release date
            final_releases = sorted(
                release_by_group.values(), key=lambda r: r.release_date
            )

            return final_releases

        def get_filtered_releases(
            creator, role, release_type=None, recording_type=None
        ):
            query = Release.objects.filter(
                releaserole__role__name__in=role, releaserole__creator=creator
            )
            if release_type:
                query = query.filter(release_type=release_type)
            if recording_type:
                query = query.filter(recording_type=recording_type)

            query = query.order_by("release_date")
            return get_releases_by_type_and_group(query)

        context.update(
            {
                "All_releases_as_performer": get_filtered_releases(
                    creator, roles_as_performer
                ),
                "boxset_releases_as_performer": get_filtered_releases(
                    creator, roles_as_performer, "Box Set"
                ),
                "LPs_as_performer": get_filtered_releases(
                    creator, roles_as_performer, "LP"
                ),
                "studio_LPs_as_performer": get_filtered_releases(
                    creator, roles_as_performer, "LP", "Studio"
                ),
                "live_LPs_as_performer": get_filtered_releases(
                    creator, roles_as_performer, "LP", "Live"
                ),
                "compilation_LPs_as_performer": get_filtered_releases(
                    creator, roles_as_performer, "LP", "Compilation"
                ),
                "EPs_as_performer": get_filtered_releases(
                    creator, roles_as_performer, "EP"
                ),
                "studio_EPs_as_performer": get_filtered_releases(
                    creator, roles_as_performer, "EP", "Studio"
                ),
                "live_EPs_as_performer": get_filtered_releases(
                    creator, roles_as_performer, "EP", "Live"
                ),
                "compilation_EPs_as_performer": get_filtered_releases(
                    creator, roles_as_performer, "EP", "Compilation"
                ),
                "singles_as_performer": get_filtered_releases(
                    creator, roles_as_performer, "Single"
                ),
                "studio_singles_as_performer": get_filtered_releases(
                    creator, roles_as_performer, "Single", "Studio"
                ),
                "live_singles_as_performer": get_filtered_releases(
                    creator, roles_as_performer, "Single", "Live"
                ),
                "demo_singles_as_performer": get_filtered_releases(
                    creator, roles_as_performer, "Single", "Demo"
                ),
            }
        )

        release_roles = (
            ReleaseRole.objects.exclude(
                role__name__in=["Performer", "Conductor", "Lyricist", "Composer"]
            )
            .values_list("role__name", flat=True)
            .distinct()
        )

        releases = {}

        for role in release_roles:
            # General case for other roles
            role_releases = (
                Release.objects.filter(
                    releaserole__role__name=role, releaserole__creator=creator
                )
                .exclude(release_type="Single")
                .order_by("release_date")
            )

            # Update context with releases filtered by role, excluding "Performer"
            if role_releases:
                releases[f"As {role}"] = role_releases

        context["releases"] = releases

        track_roles = (
            TrackRole.objects.exclude(
                role__name__in=[
                    "Conductor",
                    "Lyricist",
                    "Composer",
                    "Songwriter",
                ]
            )
            .values_list("role__name", flat=True)
            .distinct()
        )
        tracks = {}

        for role in track_roles:
            # Filter tracks for the current role and order them by release date
            role_tracks = Track.objects.filter(
                trackrole__role__name=role, trackrole__creator=creator
            ).order_by("release_date")

            # Dynamically update the context with tracks filtered by role
            if role_tracks:
                tracks[f"As {role}"] = role_tracks

        # Update context
        context["tracks"] = tracks

        work_roles = (
            ListenWorkRole.objects.filter(
                role__name__in=["Lyricist", "Composer", "Songwriter"],
            )
            .values_list("role__name", flat=True)
            .distinct()
        )
        works = {}

        for role in work_roles:
            # Filter tracks for the current role and order them by release date
            role_works = ListenWork.objects.filter(
                workrole__role__name=role, workrole__creator=creator
            ).order_by("release_date")

            # Dynamically update the context with works filtered by role
            if role_works:
                works[f"As {role}"] = role_works

        # Update context
        context["works"] = works

        context["audiobook_as_narrator"] = Audiobook.objects.filter(
            audiobookrole__role__name="Narrator", audiobookrole__creator=creator
        ).order_by("release_date")

        context["listenworks_count"] = (
            ListenWork.objects.filter(workrole__creator=creator).distinct().count()
        )
        context["tracks_count"] = (
            Track.objects.filter(trackrole__creator=creator).distinct().count()
        )
        context["releases_count"] = (
            Release.objects.filter(releaserole__creator=creator).distinct().count()
        )
        context["audiobooks_count"] = (
            Audiobook.objects.filter(audiobookrole__creator=creator).distinct().count()
        )

        # watch
        ## as casts
        context["movies_as_cast"] = (
            Movie.objects.filter(moviecasts__creator=creator)
            .distinct()
            .annotate(
                annotated_earliest_release_date=Min(
                    "region_release_dates__release_date"
                ),
                character_name=F("moviecasts__character_name"),
            )
            .order_by("annotated_earliest_release_date")
        )
        context["series_as_cast"] = (
            Series.objects.filter(episodes__episodecasts__creator=creator)
            .annotate(
                episode_count=Count("episodes"),
                character_name=F("episodes__episodecasts__character_name"),
            )
            .distinct()
            .order_by("release_date")
        )
        ## as staff

        movie_roles = (
            MovieRole.objects.values_list("role__name", flat=True)
            .distinct()
            .order_by("role__name")
        )
        movies = {}

        for role in movie_roles:
            # Filter tracks for the current role and order them by release date
            role_movies = (
                Movie.objects.filter(
                    movieroles__role__name=role, movieroles__creator=creator
                )
                .distinct()
                .annotate(
                    annotated_earliest_release_date=Min(
                        "region_release_dates__release_date"
                    )
                )
                .order_by("annotated_earliest_release_date")
            )

            # Dynamically update the context with works filtered by role
            if role_movies:
                movies[f"As {role}"] = role_movies

        context["movies"] = movies

        series_role_names = SeriesRole.objects.values_list(
            "role__name", flat=True
        ).distinct()
        episode_role_names = EpisodeRole.objects.values_list(
            "role__name", flat=True
        ).distinct()

        combined_roles = sorted(set(list(series_role_names) + list(episode_role_names)))

        series_info = {}

        for role in combined_roles:
            # Prepare a container for combined series and episode data
            combined_series_data = []

            # Fetch series directly associated with the creator for a given role in SeriesRole
            role_series_direct = Series.objects.filter(
                seriesroles__role__name=role, seriesroles__creator=creator
            ).distinct()

            # Include series based on episode roles in EpisodeRole
            role_series_from_episodes = Series.objects.filter(
                episodes__episoderoles__role__name=role,
                episodes__episoderoles__creator=creator,
            ).distinct()

            # Combine and de-duplicate series from both direct and episode-derived associations
            all_role_series = (
                role_series_direct | role_series_from_episodes
            ).distinct()

            for series in all_role_series:
                # Initial series data, episode count to be added
                series_data = {
                    "series": series,
                    "episode_count": 0,
                }

                # Fetch episodes for this series and role, count them and get the earliest release date
                episodes = Episode.objects.filter(
                    episoderoles__role__name=role,
                    episoderoles__creator=creator,
                    series=series,
                ).annotate(earliest_release_date=Min("release_date"))

                if episodes:
                    series_data["episode_count"] = episodes.count()

                combined_series_data.append(series_data)

            # Only add to the context if there's at least one series for this role
            if combined_series_data:
                series_info[f"As {role}"] = combined_series_data

        context["series"] = series_info

        context["movies_count"] = (
            Movie.objects.filter(
                Q(movieroles__creator=creator) | Q(moviecasts__creator=creator)
            )
            .distinct()
            .count()
        )
        context["series_count"] = (
            Series.objects.filter(
                Q(seriesroles__creator=creator)
                | Q(episodes__episodecasts__creator=creator)
                | Q(episodes__episoderoles__creator=creator)
            )
            .distinct()
            .count()
        )

        # play
        def get_games_by_role(role, creator):
            # Find games where the creator has this role
            games = Game.objects.filter(
                gameroles__role__name=role, gameroles__creator=creator
            ).distinct()

            # Create a dictionary to map game IDs to games
            game_dict = {game.id: game for game in games}

            # Create a dictionary to hold game works
            work_dict = {}

            # Try to find any PlayWork that matches the role and creator
            game_works = PlayWork.objects.filter(
                workrole__role__name=role, workrole__creator=creator
            ).distinct()

            # Add works to the work_dict and remove any corresponding games from game_dict
            for work in game_works:
                related_games = Game.objects.filter(work=work)
                for game in related_games:
                    if game.id in game_dict:
                        del game_dict[game.id]
                work_dict[work.id] = work

            # Combine dictionaries into one
            combined_dict = {**game_dict, **work_dict}

            # Sort by release date
            final_list = sorted(
                combined_dict.values(),
                key=lambda x: (
                    x.first_release_date
                    if hasattr(x, "first_release_date")
                    else x.region_release_dates.aggregate(Min("release_date"))[
                        "release_date__min"
                    ]
                ),
            )

            return final_list

        game_roles = (
            GameRole.objects.values_list("role__name", flat=True)
            .distinct()
            .order_by("role__name")
        )

        games = {}
        has_games = False  # Initialize the flag as False

        for role in game_roles:
            role_games = get_games_by_role(role, creator)
            games[f"As {role}"] = role_games
            if (
                role_games and not has_games
            ):  # Check if there are any games and update has_games accordingly
                has_games = True

        context["games"] = games
        context["has_games"] = has_games
        context["games_as_cast"] = (
            Game.objects.filter(gamecasts__creator=creator)
            .distinct()
            .annotate(
                annotated_earliest_release_date=Min(
                    "region_release_dates__release_date"
                )
            )
            .order_by("annotated_earliest_release_date")
        )

        context["gameworks_count"] = (
            PlayWork.objects.filter(workrole__creator=creator).distinct().count()
        )
        context["games_count"] = (
            Game.objects.filter(
                Q(gameroles__creator=creator) | Q(gamecasts__creator=creator)
            )
            .distinct()
            .count()
        )

        context["contributors"] = get_contributors(creator)

        context["birth_location_label"] = get_location_labels(creator.birth_location)
        context["death_location_label"] = get_location_labels(creator.death_location)
        context["origin_location_label"] = get_location_labels(creator.origin_location)
        return context


class CreatorUpdateView(LoginRequiredMixin, UpdateView):
    model = Creator
    form_class = CreatorForm
    template_name = "entity/creator_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["memberof"] = MemberOfFormSet(self.request.POST, instance=self.object)
        else:
            data["memberof"] = MemberOfFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        memberof = context["memberof"]
        if not all(memberof_form.is_valid() for memberof_form in memberof):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if memberof.is_valid():
                memberof.instance = self.object
                memberof.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("entity:creator_detail", kwargs={"pk": self.object.pk})


class RoleCreateView(LoginRequiredMixin, CreateView):
    model = Role
    fields = ["name", "domain", "category"]
    template_name = "entity/role_create.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse_lazy("activity_feed:activity_feed")


class RoleUpdateView(LoginRequiredMixin, UpdateView):
    model = Role
    fields = ["name", "domain", "category"]
    template_name = "entity/role_update.html"

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse_lazy("activity_feed:activity_feed")


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class RoleDetailView(LoginRequiredMixin, DetailView):
    model = Role
    template_name = "entity/role_detail.html"


class CreatorAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Creator.objects.all()

        if self.q:
            qs = qs.filter(
                Q(name__icontains=self.q) | Q(other_names__icontains=self.q)
            ).distinct()

            return qs

        return Creator.objects.none()

    def get_result_label(self, item):
        if item.active_years:
            active_years = item.active_years
            label = "{} ({})".format(item.name, active_years)
        else:
            # Get the birth and death years
            birth_year = item.birth_date[:4] if item.birth_date else "?"
            death_year = item.death_date[:4] if item.death_date else ""

            # Format the label
            label = "{} ({} - {})".format(item.name, birth_year, death_year)

        return mark_safe(label)


class GroupAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Creator.objects.exclude(creator_type="person")

        if self.q:
            qs = qs.filter(
                Q(name__icontains=self.q) | Q(other_names__icontains=self.q)
            ).distinct()

            return qs

        return Creator.objects.none()

    def get_result_label(self, item):
        # Get the birth and death years
        birth_year = item.birth_date[:4] if item.birth_date else "?"
        death_year = item.death_date[:4] if item.death_date else ""

        # Format the label
        label = "{} ({} - {})".format(item.name, birth_year, death_year)

        return mark_safe(label)


class RoleAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Role.objects.none()

        domain = self.forwarded.get("domain", None)
        qs = Role.objects.all()

        if domain:
            qs = qs.filter(domain=domain)

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs.order_by("name")


class CompanyCreateView(LoginRequiredMixin, CreateView):
    model = Company
    form_class = CompanyForm
    template_name = "entity/company_create.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["other_names"].widget = forms.TextInput()
        return form

    def get_success_url(self):
        return reverse_lazy("entity:company_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["companyparents"] = CompanyParentFormSet(
                self.request.POST, instance=self.object
            )
            data["pastnames"] = CompanyPastNameFormSet(
                self.request.POST, instance=self.object
            )

        else:
            data["companyparents"] = CompanyParentFormSet(instance=self.object)
            data["pastnames"] = CompanyPastNameFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        companyparents = context["companyparents"]
        pastnames = context["pastnames"]
        if not all(
            companyparent_form.is_valid() for companyparent_form in companyparents
        ):
            return self.form_invalid(form)
        if not all(pastname_form.is_valid() for pastname_form in pastnames):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if companyparents.is_valid():
                companyparents.instance = self.object
                companyparents.save()
            if pastnames.is_valid():
                pastnames.instance = self.object
                pastnames.save()
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        if "wiki_url" in request.POST:
            wiki_url = request.POST.get("wiki_url")
            data = scrape_company(wiki_url)

            if data is not None:
                # Assuming self.get_form_class() returns the correct form class
                form_class = self.get_form_class()
                form = form_class(initial=data)
                form.fields["other_names"].widget = forms.TextInput()
                companyparentfromset = CompanyParentFormSet()
                pastnameformset = CompanyPastNameFormSet()
                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                        "companyparents": companyparentfromset,
                        "pastnames": pastnameformset,
                    },
                )
            else:
                # Handle the case where scraping fails
                return render(request, self.template_name, {"form": self.get_form()})

        else:
            return super().post(request, *args, **kwargs)


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class CompanyDetailView(DetailView):
    model = Company
    template_name = "entity/company_detail.html"
    context_object_name = "company"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        company = self.object

        # listen
        context["LPs"] = Release.objects.filter(
            label=company, release_type="LP"
        ).order_by("-release_date")

        context["EPs"] = Release.objects.filter(
            label=company, release_type="EP"
        ).order_by("-release_date")

        context["singles"] = Release.objects.filter(
            label=company, release_type="Single"
        ).order_by("-release_date")

        context["boxsets"] = Release.objects.filter(
            label=company, release_type="Box Set"
        ).order_by("-release_date")

        # watch
        context["movies_as_production_company"] = (
            Movie.objects.filter(studios=company)
            .annotate(
                annotated_earliest_release_date=Min(
                    "region_release_dates__release_date"
                )
            )
            .order_by("annotated_earliest_release_date")
        )
        context["movies_as_distributor"] = (
            Movie.objects.filter(distributors=company)
            .annotate(
                annotated_earliest_release_date=Min(
                    "region_release_dates__release_date"
                )
            )
            .order_by("annotated_earliest_release_date")
        )

        context["series_as_production_company"] = Series.objects.filter(
            studios=company
        ).order_by("-release_date")
        context["series_as_distributor"] = Series.objects.filter(
            distributors=company
        ).order_by("-release_date")

        # play
        context["games_as_developer"] = (
            Game.objects.filter(developers=company)
            .annotate(
                annotated_earliest_release_date=Min(
                    "region_release_dates__release_date"
                )
            )
            .order_by("annotated_earliest_release_date")
        )
        context["games_as_publisher"] = (
            Game.objects.filter(publishers=company)
            .annotate(
                annotated_earliest_release_date=Min(
                    "region_release_dates__release_date"
                )
            )
            .order_by("annotated_earliest_release_date")
        )

        # contributors
        context["contributors"] = get_contributors(company)

        context["location_label"] = get_location_labels(company.location)

        # parent companies
        context["current_parent_companies"] = company.parent_companies.filter(
            end_date=None
        ).order_by("start_date")
        context["past_parent_companies"] = company.parent_companies.exclude(
            end_date=None
        ).order_by("-end_date")
        context["past_names"] = company.past_names.all().order_by("start_date")

        return context


class CompanyUpdateView(LoginRequiredMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = "entity/company_update.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the object is locked for editing.
        obj = self.get_object()
        if obj.locked:
            return HttpResponseForbidden("This entry is locked and cannot be edited.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("entity:company_detail", kwargs={"pk": self.object.pk})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["other_names"].widget = forms.TextInput()
        return form

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["companyparents"] = CompanyParentFormSet(
                self.request.POST, instance=self.object
            )
            data["pastnames"] = CompanyPastNameFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["companyparents"] = CompanyParentFormSet(instance=self.object)
            data["pastnames"] = CompanyPastNameFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        companyparents = context["companyparents"]
        pastnames = context["pastnames"]
        if not all(
            companyparent_form.is_valid() for companyparent_form in companyparents
        ):
            return self.form_invalid(form)
        if not all(pastname_form.is_valid() for pastname_form in pastnames):
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            self.object = form.save()
            if companyparents.is_valid():
                companyparents.instance = self.object
                companyparents.save()
            if pastnames.is_valid():
                pastnames.instance = self.object
                pastnames.save()
        return super().form_valid(form)


class CompanyAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Company.objects.none()

        qs = Company.objects.all()

        if self.q:
            qs = qs.filter(
                Q(name__icontains=self.q) | Q(other_names__icontains=self.q)
            ).order_by("name")
            return qs

        return Company.objects.none()


class HistoryViewMixin:
    excluded_fields = [
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "locked",
    ]

    def get_history_data(self, model_instance):
        history_data = []
        history_queryset = model_instance.history.all().prefetch_related("history_user")
        previous_record = None

        for current_record in reversed(history_queryset):
            changed_fields = {}
            is_creation_record = previous_record is None

            for field in model_instance._meta.fields:
                if field.name in self.excluded_fields:
                    continue

                field_name = field.name
                current_value = getattr(current_record, field_name)

                if is_creation_record:
                    changed_fields[field_name] = {"from": None, "to": current_value}
                elif previous_record:
                    previous_value = getattr(previous_record, field_name)
                    if current_value != previous_value:
                        changed_fields[field_name] = {
                            "from": previous_value,
                            "to": current_value,
                        }

            if changed_fields:
                history_data.append(
                    {
                        "type": "creation" if is_creation_record else "change",
                        "changed_by": current_record.history_user,
                        "changed_at": current_record.history_date,
                        "changed_fields": changed_fields,
                    }
                )

            previous_record = current_record

        history_data.reverse()
        return history_data


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class CreatorHistoryView(HistoryViewMixin, DetailView):
    model = Creator
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        creator = self.get_object()
        context["history_data"] = self.get_history_data(creator)
        return context


@method_decorator(ratelimit(key="ip", rate="10/m", block=True), name="dispatch")
class CompanyHistoryView(HistoryViewMixin, DetailView):
    model = Company
    template_name = "entity/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_object()
        context["history_data"] = self.get_history_data(company)
        return context


def get_contributors(instance):
    """
    Retrieves a list of unique contributors for a given model instance,
    ordered by the time of their first contribution.
    """
    history_records = instance.history.all().order_by("history_date")
    contributors = list(
        {
            record.history_user: record.history_user
            for record in history_records
            if record.history_user
        }.values()
    )
    return contributors
