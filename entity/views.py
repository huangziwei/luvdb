from dal import autocomplete
from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Min, Q
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django_ratelimit.decorators import ratelimit

from listen.models import Audiobook, Release, Track
from listen.models import Work as ListenWork
from play.models import Game
from play.models import Work as GameWork
from read.models import Book
from read.models import Instance as LitInstance
from read.models import Work as LitWork
from scrape.wikipedia import scrape_company, scrape_creator
from watch.models import Episode, Movie, Series

from .forms import CompanyForm, CreatorForm
from .models import Company, Creator, Role


# Create your views here.
class CreatorCreateView(LoginRequiredMixin, CreateView):
    model = Creator
    form_class = CreatorForm
    template_name = "entity/creator_create.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("entity:creator_detail", kwargs={"pk": self.object.pk})

    def post(self, request, *args, **kwargs):
        if "wiki_url" in request.POST:
            wiki_url = request.POST.get("wiki_url")
            data = scrape_creator(wiki_url)
            form = self.form_class(initial=data)
            return render(request, self.template_name, {"form": form})
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
        def get_books_by_role(role, creator):
            # Dictionary to hold final items
            final_dict = {}

            # Step 1: Get books related to the role and creator
            books = Book.objects.filter(
                bookrole__role__name=role, bookrole__creator=creator
            ).distinct()

            for book in books:
                # Check for instances
                instances = LitInstance.objects.filter(books=book)

                # No related instances
                if not instances.exists():
                    final_dict[book.id] = book
                # Multiple related instances
                elif instances.count() > 1:
                    final_dict[book.id] = book
                # Single related instance
                else:
                    instance = instances.first()
                    # Check if instance has a related work
                    final_dict[instance.id] = instance

            # Sort the final list by publication date
            final_list = sorted(
                final_dict.values(), key=lambda x: getattr(x, "publication_date", None)
            )

            return final_list

        book_roles = [
            "Author",
            "Ghost Writer",
            "Created By",
            "Novelization By",
            "Translator",
            "Editor",
            "Introduction",
            "Foreword",
            "Afterword",
            "Annotator",
        ]
        for role in book_roles:
            context_key = f"books_as_{role.lower()}"
            context[context_key] = get_books_by_role(role, creator)

        context["lit_works"] = (
            LitWork.objects.filter(
                Q(workrole__role__name__in=book_roles, workrole__creator=creator)
            )
            .distinct()
            .order_by("publication_date")
        )

        context["litworks_count"] = creator.read_works.distinct().count()
        context["litinstances_count"] = (
            LitInstance.objects.filter(instancerole__creator=creator).distinct().count()
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
                release_by_group[
                    release
                ] = release  # Individual releases are their own "group"

            # Sort the final release list by release date
            final_releases = sorted(
                release_by_group.values(), key=lambda r: r.release_date
            )

            return final_releases

        LP_releases = Release.objects.filter(
            releaserole__role__name__in=roles_as_performer,
            releaserole__creator=creator,
            release_type__in=["LP", "Box Set"],
        ).order_by("release_date")
        EP_releases = Release.objects.filter(
            releaserole__role__name__in=roles_as_performer,
            releaserole__creator=creator,
            release_type="EP",
        ).order_by("release_date")
        single_releases = Release.objects.filter(
            releaserole__role__name__in=roles_as_performer,
            releaserole__creator=creator,
            release_type="Single",
        ).order_by("release_date")

        context["LPs_as_performer"] = get_releases_by_type_and_group(LP_releases)
        context["EPs_as_performer"] = get_releases_by_type_and_group(EP_releases)
        context["singles_as_performer"] = get_releases_by_type_and_group(
            single_releases
        )

        compilation_releases = Release.objects.filter(
            releaserole__role__name="Compiler",
            releaserole__creator=creator,
            recording_type="Compilation",
        ).order_by("release_date")
        context["releases_as_compiler"] = get_releases_by_type_and_group(
            compilation_releases
        )
        context["releases_as_liner_notes_writer"] = Release.objects.filter(
            releaserole__role__name="Liner Notes", releaserole__creator=creator
        ).order_by("release_date")

        context["tracks_as_singer"] = Track.objects.filter(
            trackrole__role__name="Singer", trackrole__creator=creator
        ).order_by("release_date")
        context["works_as_composer"] = ListenWork.objects.filter(
            workrole__role__name="Composer", workrole__creator=creator
        ).order_by("release_date")
        context["works_as_lyricist"] = ListenWork.objects.filter(
            workrole__role__name="Lyricist", workrole__creator=creator
        ).order_by("release_date")
        context["tracks_as_producer"] = Track.objects.filter(
            trackrole__role__name="Producer", trackrole__creator=creator
        ).order_by("release_date")
        context["tracks_as_arranger"] = Track.objects.filter(
            trackrole__role__name="Arranger", trackrole__creator=creator
        ).order_by("release_date")
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
        context["movies"] = (
            Movie.objects.filter(moviecasts__creator=creator)
            .distinct()
            .annotate(earliest_release_date=Min("region_release_dates__release_date"))
            .order_by("earliest_release_date")
        )
        context["series"] = (
            Series.objects.filter(episodes__episodecasts__creator=creator)
            .annotate(episode_count=Count("episodes"))
            .distinct()
            .order_by("release_date")
        )
        ## as staff
        context["movies_as_director"] = (
            Movie.objects.filter(
                movieroles__creator=creator, movieroles__role__name="Director"
            )
            .distinct()
            .annotate(earliest_release_date=Min("region_release_dates__release_date"))
            .order_by("earliest_release_date")
        )

        directed_series = Series.objects.filter(
            seriesroles__creator=creator, seriesroles__role__name="Director"
        ).distinct()

        episode_series = (
            Episode.objects.filter(
                episoderoles__creator=creator, episoderoles__role__name="Director"
            )
            .values("series__id", "series__title")
            .annotate(episode_count=Count("id"))
        )

        series_directed_info = []

        # Add series directed by the creator
        for series in directed_series:
            series_directed_info.append({"series": series, "episode_count": None})

        # Add series based on episodes directed by the creator
        for entry in episode_series:
            # Check if series is already in series_directed_info
            if any(
                info["series"].id == entry["series__id"]
                for info in series_directed_info
            ):
                # If the series is already in the list, update the episode_count
                for info in series_directed_info:
                    if info["series"].id == entry["series__id"]:
                        info["episode_count"] = entry["episode_count"]
            else:
                # If the series is not in the list, add it with the episode count
                series = Series.objects.get(pk=entry["series__id"])
                series_directed_info.append(
                    {"series": series, "episode_count": entry["episode_count"]}
                )

        # Add to context
        context["series_as_director"] = series_directed_info

        context["movies_as_writer"] = (
            Movie.objects.filter(
                movieroles__creator=creator, movieroles__role__name="Screenwriter"
            )
            .distinct()
            .annotate(earliest_release_date=Min("region_release_dates__release_date"))
            .order_by("earliest_release_date")
        )

        written_series = Series.objects.filter(
            seriesroles__creator=creator, seriesroles__role__name="Screenwriter"
        ).distinct()

        episode_series_writer = (
            Episode.objects.filter(
                episoderoles__creator=creator, episoderoles__role__name="Screenwriter"
            )
            .values("series__id", "series__title")
            .annotate(episode_count=Count("id"))
        )

        series_written_info = []

        # Add series written by the creator
        for series in written_series:
            series_written_info.append({"series": series, "episode_count": None})

        # Add series based on episodes written by the creator
        for entry in episode_series_writer:
            # Check if series is already in series_written_info
            if any(
                info["series"].id == entry["series__id"] for info in series_written_info
            ):
                # If the series is already in the list, update the episode_count
                for info in series_written_info:
                    if info["series"].id == entry["series__id"]:
                        info["episode_count"] = entry["episode_count"]
            else:
                # If the series is not in the list, add it with the episode count
                series = Series.objects.get(pk=entry["series__id"])
                series_written_info.append(
                    {"series": series, "episode_count": entry["episode_count"]}
                )

        # Add to context
        context["series_as_writer"] = series_written_info

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

            # Try to find any GameWork that matches the role and creator
            game_works = GameWork.objects.filter(
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
                key=lambda x: x.first_release_date
                if hasattr(x, "first_release_date")
                else x.region_release_dates.aggregate(Min("release_date"))[
                    "release_date__min"
                ],
            )

            return final_list

        game_roles = [
            "Writer",
            "Artist",
            "Musician",
            "Producer",
            "Director",
            "Designer",
            "Programmer",
        ]

        for role in game_roles:
            context_key = f"games_as_{role.lower()}"
            context[context_key] = get_games_by_role(role, creator)

        context["games_as_cast"] = (
            Game.objects.filter(gamecasts__creator=creator)
            .distinct()
            .annotate(earliest_release_date=Min("region_release_dates__release_date"))
            .order_by("earliest_release_date")
        )

        context["gameworks_count"] = (
            GameWork.objects.filter(workrole__creator=creator).distinct().count()
        )
        context["games_count"] = (
            Game.objects.filter(
                Q(gameroles__creator=creator) | Q(gamecasts__creator=creator)
            )
            .distinct()
            .count()
        )

        context["contributors"] = get_contributors(creator)

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

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("entity:creator_detail", kwargs={"pk": self.object.pk})


class RoleCreateView(LoginRequiredMixin, CreateView):
    model = Role
    fields = ["name", "domain"]
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
    fields = ["name", "domain"]
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
        # Get the birth and death years
        birth_year = item.birth_date[:4] if item.birth_date else "?"
        death_year = item.death_date[:4] if item.death_date else ""

        # Format the label
        label = format_html("{} ({} - {})", item.name, birth_year, death_year)

        return label


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

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
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
                return render(request, self.template_name, {"form": form})
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
            .annotate(earliest_release_date=Min("region_release_dates__release_date"))
            .order_by("earliest_release_date")
        )
        context["movies_as_distributor"] = (
            Movie.objects.filter(distributors=company)
            .annotate(earliest_release_date=Min("region_release_dates__release_date"))
            .order_by("earliest_release_date")
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
            .annotate(earliest_release_date=Min("region_release_dates__release_date"))
            .order_by("earliest_release_date")
        )
        context["games_as_publisher"] = (
            Game.objects.filter(publishers=company)
            .annotate(earliest_release_date=Min("region_release_dates__release_date"))
            .order_by("earliest_release_date")
        )

        # contributors
        context["contributors"] = get_contributors(company)

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

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["other_names"].widget = forms.TextInput()
        return form

    def get_success_url(self):
        return reverse_lazy("entity:company_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
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
