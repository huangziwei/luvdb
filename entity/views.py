from dal import autocomplete
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView

from listen.models import Release, Track
from listen.models import Work as ListenWork
from play.models import Game
from play.models import Work as GameWork
from read.models import Book
from read.models import Instance as LitInstance
from watch.models import Episode, Movie, Series

from .forms import PersonForm
from .models import Person, Role


# Create your views here.
class PersonCreateView(LoginRequiredMixin, CreateView):
    model = Person
    form_class = PersonForm
    template_name = "entity/person_create.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("entity:person_detail", kwargs={"pk": self.object.pk})


class PersonDetailView(DetailView):
    model = Person
    template_name = "entity/person_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = self.object
        # read
        context["read_works"] = person.read_works.all().order_by("publication_date")

        as_translator = LitInstance.objects.filter(
            instancerole__role__name="Translator", instancerole__person=person
        ).order_by("publication_date")
        context["as_translator"] = as_translator

        writings = Book.objects.filter(
            Q(bookrole__role__name="Introduction")
            | Q(bookrole__role__name="Afterword"),
            bookrole__person=person,
        ).order_by("publication_date")

        context["writings"] = writings

        as_editor = LitInstance.objects.filter(
            instancerole__role__name="Editor", instancerole__person=person
        ).order_by("publication_date")
        context["as_editor"] = as_editor

        as_annotator = LitInstance.objects.filter(
            instancerole__role__name="Annotator", instancerole__person=person
        ).order_by("publication_date")
        context["as_annotator"] = as_annotator

        context["litworks_count"] = person.read_works.distinct().count()
        context["litinstances_count"] = (
            LitInstance.objects.filter(instancerole__person=person).distinct().count()
        )
        context["books_count"] = (
            Book.objects.filter(bookrole__person=person).distinct().count()
        )

        # listen
        roles_as_performer = ["Singer", "Pianist", "Conductor"]

        context["LPs_as_performer"] = Release.objects.filter(
            releaserole__role__name__in=roles_as_performer,
            releaserole__person=person,
            release_type="LP",
        ).order_by("release_date")
        context["EPs_as_performer"] = Release.objects.filter(
            releaserole__role__name__in=roles_as_performer,
            releaserole__person=person,
            release_type="EP",
        ).order_by("release_date")
        context["singles_as_performer"] = Release.objects.filter(
            releaserole__role__name__in=roles_as_performer,
            releaserole__person=person,
            release_type="Single",
        ).order_by("release_date")

        context["tracks_as_singer"] = Track.objects.filter(
            trackrole__role__name="Singer", trackrole__person=person
        ).order_by("release_date")
        context["works_as_composer"] = ListenWork.objects.filter(
            workrole__role__name="Composer", workrole__person=person
        ).order_by("release_date")
        context["works_as_lyricist"] = ListenWork.objects.filter(
            workrole__role__name="Lyricist", workrole__person=person
        ).order_by("release_date")
        context["tracks_as_producer"] = Track.objects.filter(
            trackrole__role__name="Producer", trackrole__person=person
        ).order_by("release_date")
        context["tracks_as_arranger"] = Track.objects.filter(
            trackrole__role__name="Arranger", trackrole__person=person
        ).order_by("release_date")

        context["listenworks_count"] = (
            ListenWork.objects.filter(workrole__person=person).distinct().count()
        )
        context["tracks_count"] = (
            Track.objects.filter(trackrole__person=person).distinct().count()
        )
        context["releases_count"] = (
            Release.objects.filter(releaserole__person=person).distinct().count()
        )
        # watch
        ## as casts
        context["movies"] = (
            Movie.objects.filter(moviecasts__person=person)
            .distinct()
            .order_by("release_date")
        )
        context["series"] = (
            Series.objects.filter(episodes__episodecasts__person=person)
            .annotate(episode_count=Count("episodes"))
            .distinct()
            .order_by("release_date")
        )
        ## as staff
        context["movies_as_director"] = (
            Movie.objects.filter(
                movieroles__person=person, movieroles__role__name="Director"
            )
            .distinct()
            .order_by("release_date")
        )

        directed_series = Series.objects.filter(
            seriesroles__person=person, seriesroles__role__name="Director"
        ).distinct()

        episode_series = (
            Episode.objects.filter(
                episoderoles__person=person, episoderoles__role__name="Director"
            )
            .values("series__id", "series__title")
            .annotate(episode_count=Count("id"))
        )

        series_directed_info = []

        # Add series directed by the person
        for series in directed_series:
            series_directed_info.append({"series": series, "episode_count": None})

        # Add series based on episodes directed by the person
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
                movieroles__person=person, movieroles__role__name="Writer"
            )
            .distinct()
            .order_by("release_date")
        )

        written_series = Series.objects.filter(
            seriesroles__person=person, seriesroles__role__name="Writer"
        ).distinct()

        episode_series_writer = (
            Episode.objects.filter(
                episoderoles__person=person, episoderoles__role__name="Writer"
            )
            .values("series__id", "series__title")
            .annotate(episode_count=Count("id"))
        )

        series_written_info = []

        # Add series written by the person
        for series in written_series:
            series_written_info.append({"series": series, "episode_count": None})

        # Add series based on episodes written by the person
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
                Q(movieroles__person=person) | Q(moviecasts__person=person)
            )
            .distinct()
            .count()
        )
        context["series_count"] = (
            Series.objects.filter(
                Q(seriesroles__person=person)
                | Q(episodes__episodecasts__person=person)
                | Q(episodes__episoderoles__person=person)
            )
            .distinct()
            .count()
        )

        # play
        context["gameworks"] = (
            GameWork.objects.filter(
                workrole__role__name="Writer", workrole__person=person
            )
            .distinct()
            .order_by("first_release_date")
        )

        context["gameworks_count"] = (
            GameWork.objects.filter(workrole__person=person).distinct().count()
        )
        context["games_count"] = (
            Game.objects.filter(gameroles__person=person).distinct().count()
        )

        return context


class PersonUpdateView(LoginRequiredMixin, UpdateView):
    model = Person
    form_class = PersonForm
    template_name = "entity/person_update.html"

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("entity:person_detail", kwargs={"pk": self.object.pk})


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


class RoleDetailView(LoginRequiredMixin, DetailView):
    model = Role
    template_name = "entity/role_detail.html"


class PersonAutoComplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Person.objects.all()

        if self.q:
            qs = qs.filter(
                Q(name__icontains=self.q) | Q(other_names__icontains=self.q)
            ).distinct()

            return qs

        return Person.objects.none()

    def get_result_label(self, item):
        # Get the birth and death years
        birth_year = item.birth_date[:4] if item.birth_date else "Unk."
        death_year = item.death_date[:4] if item.death_date else "Pres."

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

        return qs
