# LʌvDB is ...

An opinionated, self-hosted alternative to Goodreads, IMDB, Discogs, and ultimately, Douban.

It's a Django-based cataloguing webapp, which allows you to keep track of your books, movies, music, and games. It also includes an activity feed, where you can follow your friends and see what they're reading, watching, listening to, and playing.

## Preview

I host an instance of the app at [luvdb.com](https://luvdb.com). It's currently not open for registration and probably never will. If you want to get the feel of the app, you can go and see some of the pages here:

- [Read](https://luvdb.com/read/recent/)
- [Watch](https://luvdb.com/watch/recent/)
- [Listen](https://luvdb.com/listen/recent/)

## Try it out locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
touch .env
python -c 'from django.core.management.utils import get_random_secret_key; print("SECRET_KEY="+get_random_secret_key())' > .env
echo "DEBUG=True" >> .env
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py makemigrations
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py migrate
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py createsuperuser
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py runserver
```
