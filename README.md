# LʌvDB is ...

An opinionated, self-hosted alternative to Goodreads, IMDB, Discogs, and ultimately, Douban.

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
