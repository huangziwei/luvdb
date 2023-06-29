# LʌvDB

A [Douban](https://www.douban.com/) clone with LOVE. Built with Django and Bootstrap.

## Features / Roadmap (subject to change)

- [x] User Account
    - [ ] Delete Account
- [x] Activity Feed
    - [x] Follow/Unfollow
    - [ ] Block
- [x] Entity
    - [x] Person
- [x] Write
    - [x] Say
    - [x] Pin 
    - [x] Post
    - [x] Repost 
    - [x] Comment 
- [x] Play
    - [x] Game
    - [x] Series
    - [ ] Cast
    - [x] Check-In
- [x] Read
    - [x] Work
    - [x] Instance
    - [x] Book
    - [x] Periodical
        - [x] Issue
    - [x] Publisher
    - [x] Series
    - [x] Check-In
- [ ] Listen
    - [ ] Track
    - [ ] Cover
    - [ ] Release
    - [ ] Podcast
        - [ ] Episode
    - [ ] Check-In
- [ ] Watch
    - [ ] Movie
    - [ ] Series
        - [ ] Season
            - [ ] Episode
    - [ ] Cast
    - [ ] Check-In
- [ ] Visit
    - [ ] Location
    - [ ] Check-In


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
