# LʌvDB

A [Douban](https://www.douban.com/) with Love. Built with Django and Bootstrap.

## Features / Roadmap (subject to change)

- [x] User Profile
- [x] Activity Feed
    - [x] Follow/Unfollow
- [x] Entity
    - [x] Person
- [x] Write
    - [x] Say
    - [x] Pin 
    - [x] Post
    - [x] Repost 
    - [x] Comment 
    - [x] Check-In
- [x] Play
    - [x] Game
    - [ ] Cast
- [x] Read
    - [x] Work
    - [x] Instance
    - [x] Book
    - [x] Periodical
        - [x] Issue
    - [x] Publisher
    - [ ] Series
- [ ] Listen
    - [ ] Track
    - [ ] Cover
    - [ ] Release
    - [ ] Podcast
        - [ ] Episode
- [ ] Watch
    - [ ] Movie
    - [ ] Series
        - [ ] Season
            - [ ] Episode
    - [ ] Cast


## Installation

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
