import re
import xml.etree.ElementTree as etree
from itertools import groupby
from operator import attrgetter

import markdown
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from markdown.inlinepatterns import InlineProcessor


# media card in markdown blockquote ```card```
def media_card(source, language, css_class, options, md, **kwargs):
    # Determine the media type from the source URL
    parts = source.strip().split("/")
    if len(parts) < 3:
        return '<div class="error">Invalid media URL format</div>'

    media_type = parts[-4]

    # Call the appropriate function based on the media type
    if media_type == "read":
        if "book" in source:
            return book_card(source, language, css_class, options, md, **kwargs)
    elif media_type == "watch":
        # Further determine if it's a movie or a series
        if "movie" in source:
            return movie_card(source, language, css_class, options, md, **kwargs)
        elif "series" in source:
            return series_card(source, language, css_class, options, md, **kwargs)
    elif media_type == "listen":
        if "release" in source:
            return release_card(source, language, css_class, options, md, **kwargs)
        elif "audiobook" in source:
            return audiobook_card(source, language, css_class, options, md, **kwargs)
        elif "podcast" in source:
            return podcast_card(source, language, css_class, options, md, **kwargs)
    elif media_type == "play":
        if "game" in source:
            return game_card(source, language, css_class, options, md, **kwargs)
    else:
        return '<div class="p-3 error">Unsupported media type</div>'


def book_card(source, language, css_class, options, md, **kwargs):
    from read.models import Book

    # Extract book_id from the source
    book_id = source.strip().split("/")[-2]

    # Fetch the Book instance
    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        return '<div class="error">Book not found</div>'

    # Format the Book data into HTML
    cover_image = book.cover.url if book.cover else None
    cover_image_tag = (
        f'<img src="{cover_image}" alt="{book.title} cover" class="img-fluid cover-border" loading="lazy">'
        if cover_image
        else f'<div class="cover-placeholder">{book.title}</div>'
    )

    try:
        book_roles = book.bookrole_set.all()
        book_roles_html = ""
        for role_name, roles in groupby(book_roles, key=attrgetter("role.name")):
            role_html_parts = [
                f'<a href="/entity/creator/{br.creator.id}">{br.alt_name or br.creator.name}</a>'
                for br in roles
            ]
            role_names = " / ".join(role_html_parts)
            plural_suffix = "s" if len(role_html_parts) > 1 else ""
            book_roles_html += f'<div><span class="text-muted">{role_name}{plural_suffix}:</span> {role_names}</div>'
    except AttributeError:
        print("Error in book_card() function")

    try:
        book_genre_html = ""
        book_genres = book.get_genres()
        if len(book_genres) > 0:
            book_genre_html = f"""<div>
                    <span class="text-muted">Genres:</span>
                    {" / ".join([f'<a href="/read/genre/{genre.slug}">{genre.name}</a>' for genre in book_genres])}
                </div>"""
    except AttributeError:
        print("Error in book_card() function")

    return f"""<div class="media-card d-flex flex-row p-3 mb-2">
            <div class="mt-1 mb-3 mb-md-0 flex-shrink-0 checkin-cover">
                {cover_image_tag}
            </div>
            <div class="flex-grow-1 ms-3">
                <a href="/read/book/{book.id}" class="text-decoration-none h-cite p-name">
                    <div class="fs-5">{book.title}</div>
                </a>
                {book_roles_html}
                <div>
                    <span class="text-muted">Publisher:</span>
                    <a href="/entity/company/{book.publisher.id}">{book.publisher.name}</a>
                </div>
                {book_genre_html}
                <div>
                    <span class="text-muted">Date:</span>
                    {book.publication_date}
                </div>
            </div>
        </div>
    """


def audiobook_card(source, language, css_class, options, md, **kwargs):
    from listen.models import Audiobook

    # Extract audiobook_id from the source
    audiobook_id = source.strip().split("/")[-2]

    # Fetch the Book instance
    try:
        audiobook = Audiobook.objects.get(id=audiobook_id)
    except Audiobook.DoesNotExist:
        return '<div class="error">Book not found</div>'

    # Format the Book data into HTML
    cover_image = audiobook.cover.url if audiobook.cover else None
    cover_image_tag = (
        f'<img src="{cover_image}" alt="{audiobook.title} cover" class="img-fluid cover-border" loading="lazy">'
        if cover_image
        else f'<div class="cover-placeholder">{audiobook.title}</div>'
    )

    try:
        audiobook_roles = audiobook.audiobookrole_set.all()
        roles_html = ""
        for role_name, roles in groupby(audiobook_roles, key=attrgetter("role.name")):
            role_html_parts = [
                f'<a href="/entity/creator/{br.creator.id}">{br.alt_name or br.creator.name}</a>'
                for br in roles
            ]
            role_names = " / ".join(role_html_parts)
            plural_suffix = "s" if len(role_html_parts) > 1 else ""
            roles_html += f'<div><span class="text-muted">{role_name}{plural_suffix}:</span> {role_names}</div>'
    except AttributeError:
        print("Error in audiobook_card() function")

    try:
        genre_html = ""
        genres = audiobook.get_genres()
        if len(genres) > 0:
            genre_html = f"""
                <div>
                    <span class="text-muted">Genres:</span>
                    {" / ".join([f'<a href="/read/genre/{genre.slug}">{genre.name}</a>' for genre in genres])}
                </div>
            """
    except AttributeError:
        print("Error in book_card() function")

    return f"""<div class="media-card d-flex flex-row p-3 mb-2">
            <div class="mt-1 mb-3 mb-md-0 flex-shrink-0 checkin-cover">
                {cover_image_tag}
            </div>
            <div class="flex-grow-1 ms-3">
                <a href="/listen/audiobook/{audiobook.id}" class="text-decoration-none h-cite p-name">
                    <div class="fs-5">{audiobook.title}</div>
                </a>
                {roles_html}
                <div>
                    <span class="text-muted">Publisher:</span>
                    <a href="/entity/company/{audiobook.publisher.id}">{audiobook.publisher.name}</a>
                </div>
                {genre_html}
                <div>
                    <span class="text-muted">Date:</span>
                    {audiobook.release_date}
                </div>
            </div>
        </div>
    """


def movie_card(source, language, css_class, options, md, **kwargs):
    from watch.models import Movie

    # Extract movie_id from the source
    movie_id = source.strip().split("/")[-2]

    # Fetch the Movie instance
    try:
        movie = Movie.objects.get(id=movie_id)
    except Movie.DoesNotExist:
        return '<div class="error">Movie not found</div>'

    # Format the Movie data into HTML
    poster_image = movie.poster.url if movie.poster else None
    poster_image_tag = (
        f'<img src="{poster_image}" alt="{movie.title} cover" class="img-fluid cover-border" loading="lazy">'
        if poster_image
        else f'<div class="cover-placeholder">{movie.title}</div>'
    )

    # Handling movie roles
    roles_html = ""
    movie_roles = movie.movieroles.all().order_by("role__name")
    for role_name, roles in groupby(movie_roles, key=attrgetter("role.name")):
        role_html_parts = [
            f'<a href="/entity/creator/{mr.creator.id}">{mr.alt_name or mr.creator.name}</a>'
            for mr in roles
        ]
        role_names = " / ".join(role_html_parts)
        plural_suffix = "s" if len(role_html_parts) > 1 else ""
        roles_html += f'<div><span class="text-muted">{role_name}{plural_suffix}:</span> {role_names}</div>'

    # Studios and Distributors
    studio_html = _generate_entity_html(movie.studios.all(), "Studio", "company")
    distributor_html = _generate_entity_html(
        movie.distributors.all(), "Distributor", "company"
    )

    # Crew and Cast
    crew_and_cast_html = f"""
                <div>
                    <span class="text-muted">Crew and Cast:</span>
                    <a href="/watch/movie/{movie.id}/cast">View All</a>
                </div>
            """

    # Genres
    try:
        genre_html = ""
        genres = movie.genres.all()
        if len(genres) > 0:
            genre_html = f"""
                <div>
                    <span class="text-muted">Genres:</span>
                    {" / ".join([f'<a href="/watch/genre/{genre.name}">{genre.name}</a>' for genre in genres])}
                </div>
            """
    except AttributeError:
        print("Error in book_card() function")

    # Release Date
    region_release_dates = movie.region_release_dates.all().order_by("release_date")
    if region_release_dates.exists():
        earliest_release = region_release_dates.first()
        release_date_html = f'<div><span class="text-muted">Date:</span> {earliest_release.release_date} ({earliest_release.region})</div>'
    else:
        release_date_html = ""

    return f"""<div class="media-card d-flex flex-row p-3 mb-2">
                    <div class="mt-1 mb-3 mb-md-0 flex-shrink-0 checkin-cover">
                        {poster_image_tag}
                    </div>
                    <div class="flex-grow-1 ms-3">
                        <a href="/watch/movie/{movie.id}" class="text-decoration-none h-cite p-name">
                            <div class="fs-5">{movie.title}</div>
                        </a>
                        {roles_html}
                        {studio_html}
                        {distributor_html}
                        {genre_html}
                        {crew_and_cast_html}
                        {release_date_html}
                    </div>
                </div>
            """


def _generate_entity_html(entities, label, url_namespace):
    if not entities.exists():
        return ""

    plural_suffix = "s" if entities.count() > 1 else ""
    entity_links = " / ".join(
        [
            f'<a href="/entity/{url_namespace}/{entity.id}">{entity.name}</a>'
            for entity in entities
        ]
    )
    return f'<div><span class="text-muted">{label}{plural_suffix}:</span> {entity_links}</div>'


def series_card(source, language, css_class, options, md, **kwargs):
    from watch.models import Series

    # Extract series_id from the source
    series_id = source.strip().split("/")[-2]

    # Fetch the Movie instance
    try:
        series = Series.objects.get(id=series_id)
    except Series.DoesNotExist:
        return '<div class="error">Series not found</div>'

    # Format the Movie data into HTML
    poster_image = series.poster.url if series.poster else None
    poster_image_tag = (
        f'<img src="{poster_image}" alt="{series.title} cover" class="img-fluid cover-border" loading="lazy">'
        if poster_image
        else f'<div class="cover-placeholder">{series.title}</div>'
    )

    # Handling movie roles
    roles_html = ""
    series_roles = series.seriesroles.all().order_by("role__name")
    for role_name, roles in groupby(series_roles, key=attrgetter("role.name")):
        role_html_parts = [
            f'<a href="/entity/creator/{mr.creator.id}">{mr.alt_name or mr.creator.name}</a>'
            for mr in roles
        ]
        role_names = " / ".join(role_html_parts)
        plural_suffix = "s" if len(role_html_parts) > 1 else ""
        roles_html += f'<div><span class="text-muted">{role_name}{plural_suffix}:</span> {role_names}</div>'

    # Studios and Distributors
    studio_html = _generate_entity_html(series.studios.all(), "Studio", "company")
    distributor_html = _generate_entity_html(
        series.distributors.all(), "Distributor", "company"
    )

    # Crew and Cast
    crew_and_cast_html = f"""
                <div>
                    <span class="text-muted">Crew and Cast:</span>
                    <a href="/watch/series/{series.id}/cast">View All</a>
                </div>
            """

    # Genres
    try:
        genre_html = ""
        genres = series.genres.all()
        if len(genres) > 0:
            genre_html = f"""<div>
                    <span class="text-muted">Genres:</span>
                    {" / ".join([f'<a href="/watch/genre/{genre.name}">{genre.name}</a>' for genre in genres])}
                </div>
            """
    except AttributeError:
        print("Error in book_card() function")

    # Release Date
    release_date_html = (
        f'<div><span class="text-muted">Date:</span> {series.release_date}</div>'
        if series.release_date
        else ""
    )

    return f"""<div class="media-card d-flex flex-row p-3 mb-2">
            <div class="mt-1 mb-3 mb-md-0 flex-shrink-0 checkin-cover">
                {poster_image_tag}
            </div>
            <div class="flex-grow-1 ms-3">
                <a href="/watch/series/{series.id}" class="text-decoration-none h-cite p-name">
                    <div class="fs-5">{series.title}</div>
                </a>
                {roles_html}
                {studio_html}
                {distributor_html}
                {genre_html}
                {crew_and_cast_html}
                {release_date_html}
            </div>
        </div>
    """


def release_card(source, language, css_class, options, md, **kwargs):
    from listen.models import Release

    # Extract release_id from the source
    release_id = source.strip().split("/")[-2]

    # Fetch the Movie instance
    try:
        release = Release.objects.get(id=release_id)
    except Release.DoesNotExist:
        return '<div class="error">Release not found</div>'

    # Format the Movie data into HTML
    cover_image = release.cover.url if release.cover else None
    cover_image_tag = (
        f'<img src="{cover_image}" alt="{release.title} cover" class="img-fluid cover-border" loading="lazy">'
        if cover_image
        else f'<div class="cover-placeholder">{release.title}</div>'
    )

    # Handling movie roles
    roles_html = ""
    release_roles = release.releaserole_set.all()
    for role_name, roles in groupby(release_roles, key=attrgetter("role.name")):
        role_html_parts = [
            f'<a href="/entity/creator/{mr.creator.id}">{mr.alt_name or mr.creator.name}</a>'
            for mr in roles
        ]
        role_names = " / ".join(role_html_parts)
        plural_suffix = "s" if len(role_html_parts) > 1 else ""
        roles_html += f'<div><span class="text-muted">{role_name}{plural_suffix}:</span> {role_names}</div>'

    # Studios and Distributors
    label_html = _generate_entity_html(release.label.all(), "Label", "company")

    # Genres
    try:
        genre_html = ""
        genres = release.get_genres()
        if len(genres) > 0:
            genre_html = f"""
                <div>
                    <span class="text-muted">Genres:</span>
                    {" / ".join([f'<a href="/watch/genre/{genre.name}">{genre.name}</a>' for genre in genres])}
                </div>
            """
    except AttributeError:
        print("Error in book_card() function")

    # Release Date
    release_region_html = (
        f"({release.release_region})" if release.release_region else ""
    )
    release_date_html = (
        f'<div><span class="text-muted">Date:</span> {release.release_date} {release_region_html} </div>'
        if release.release_date
        else ""
    )

    return f"""<div class="media-card d-flex flex-row p-3 mb-2">
            <div class="mt-1 mb-3 mb-md-0 flex-shrink-0 checkin-cover">
                {cover_image_tag}
            </div>
            <div class="flex-grow-1 ms-3">
                <a href="/listen/release/{release.id}" class="text-decoration-none h-cite p-name">
                    <div class="fs-5">{release.title}</div>
                </a>
                {roles_html}
                {label_html}
                {genre_html}
                {release_date_html}
            </div>
        </div>
    """


def podcast_card(source, language, css_class, options, md, **kwargs):
    from listen.models import Podcast

    # Extract podcast_id from the source
    podcast_id = source.strip().split("/")[-2]

    # Fetch the Movie instance
    try:
        podcast = Podcast.objects.get(id=podcast_id)
    except Podcast.DoesNotExist:
        return '<div class="error">Podcast not found</div>'

    # Format the Movie data into HTML
    cover_image = podcast.cover.url if podcast.cover else None
    cover_image_tag = (
        f'<img src="{cover_image}" alt="{podcast.title} cover" class="img-fluid cover-border" loading="lazy">'
        if cover_image
        else f'<div class="cover-placeholder">{podcast.title}</div>'
    )

    return f"""<div class="media-card d-flex flex-row p-3 mb-2">
            <div class="mt-1 mb-3 mb-md-0 flex-shrink-0 checkin-cover">
                {cover_image_tag}
            </div>
            <div class="flex-grow-1 ms-3">
                <a href="/listen/podcast/{podcast.id}" class="text-decoration-none h-cite p-name">
                    <div class="fs-5">{podcast.title}</div>
                </a>
                 <div class="text-muted">{podcast.description}</div>
            </div>
        </div>
    """


def game_card(source, language, css_class, options, md, **kwargs):
    from play.models import Game

    # Extract game_id from the source
    game_id = source.strip().split("/")[-2]

    # Fetch the Game instance
    try:
        game = Game.objects.get(id=game_id)
    except Game.DoesNotExist:
        return '<div class="error">Game not found</div>'

    # Format the Game data into HTML
    cover_image = game.cover.url if game.cover else None
    cover_image_tag = (
        f'<img src="{cover_image}" alt="{game.title} cover" class="img-fluid cover-border" loading="lazy">'
        if cover_image
        else f'<div class="cover-placeholder">{game.title}</div>'
    )

    # # Handling game roles
    roles_html = ""
    game_roles = game.gameroles.all().order_by("role__name")
    for role_name, roles in groupby(game_roles, key=attrgetter("role.name")):
        role_html_parts = [
            f'<a href="/entity/creator/{mr.creator.id}">{mr.alt_name or mr.creator.name}</a>'
            for mr in roles
        ]
        role_names = " / ".join(role_html_parts)
        plural_suffix = "s" if len(role_html_parts) > 1 else ""
        roles_html += f'<div><span class="text-muted">{role_name}{plural_suffix}:</span> {role_names}</div>'

    # Studios and Distributors
    developer_html = _generate_entity_html(
        game.developers.all(), "Developer", "company"
    )
    publisher_html = _generate_entity_html(
        game.publishers.all(), "Publisher", "company"
    )

    # # Genres
    try:
        genre_html = ""
        genres = game.work.genres.all()
        if len(genres) > 0:
            genre_html = f"""
                <div>
                    <span class="text-muted">Genres:</span>
                    {" / ".join([f'<a href="/play/genre/{genre.slug}">{genre.name}</a>' for genre in genres])}
                </div>
            """
    except AttributeError:
        print("Error in book_card() function")

    # Crew and Cast
    crew_and_cast_html = f"""
                <div>
                    <span class="text-muted">Crew and Cast:</span>
                    <a href="/play/game/{game.id}/cast">View All</a>
                </div>
            """
    # Release Date
    region_release_dates = game.region_release_dates.all().order_by("release_date")
    if region_release_dates.exists():
        earliest_release = region_release_dates.first()
        release_date_html = f'<div><span class="text-muted">Date:</span> {earliest_release.release_date} ({earliest_release.region})</div>'
    else:
        release_date_html = ""

    return f"""<div class="media-card d-flex flex-row p-3 mb-2">
            <div class="mt-1 mb-3 mb-md-0 flex-shrink-0 checkin-cover">
                {cover_image_tag}
            </div>
            <div class="flex-grow-1 ms-3">
                <a href="/play/game/{game.id}" class="text-decoration-none h-cite p-name">
                    <div class="fs-5">{game.title}</div>
                </a>
                {roles_html}
                {developer_html}
                {publisher_html}
                {genre_html}
                {crew_and_cast_html}
                {release_date_html}
            </div>
        </div>
    """


class MentionPattern(InlineProcessor):
    def handleMatch(self, m, data):
        username = m.group(1)
        try:
            user = get_user_model().objects.get(username=username)
            url = reverse("accounts:detail", args=[username])
            a = etree.Element("a")
            a.text = f"@{username}"
            a.set("href", url)
            return a, m.start(0), m.end(0)
        except get_user_model().DoesNotExist:
            span = etree.Element("span")
            span.text = f"@{username}"
            return span, m.start(0), m.end(0)


class MentionExtension(markdown.Extension):
    def extendMarkdown(self, md):
        # Allow dots inside the username, but not at the end
        MENTION_PATTERN = r"(?<![:/])@([\w]+(?:\.[\w]+)*)"
        mentionPattern = MentionPattern(MENTION_PATTERN, md)
        md.inlinePatterns.register(mentionPattern, "mention", 175)


class ImagePattern(InlineProcessor):
    def handleMatch(self, m, data):
        from write.models import Photo

        caption = m.group(1)
        image_id = m.group(2)
        try:
            photo = Photo.objects.get(photo_id=image_id)
            url = photo.photo.url
        except Photo.DoesNotExist:
            url = f"{settings.MEDIA_URL}photos/default.jpg"  # Fallback URL if the image does not exist

        # Create the img element
        img = etree.Element("img")
        img.set("src", url)
        img.set("alt", caption)  # Set the caption as the alt text

        return img, m.start(0), m.end(0)


class ImageExtension(markdown.Extension):
    def extendMarkdown(self, md):
        # Pattern for matching the image syntax `![](luvbild_xxxxxxx...)`
        IMAGE_PATTERN = r"!\[([^\]]*)\]\((luvbild_[\w\d]+)\)"
        imagePattern = ImagePattern(IMAGE_PATTERN, md)
        md.inlinePatterns.register(imagePattern, "image", 175)
