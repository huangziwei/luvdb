# LʌvDB

A opinionated [Douban](https://www.douban.com/) clone.

## Features / Roadmap (subject to change)

- [x] User Account
    - [ ] Delete Account
    - [ ] Export Data
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
        - [ ] Edition
    - [x] Series
    - [x] Cast
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
- [x] Listen
    - [x] Work
    - [x] Track
    - [x] Release
    - [ ] Podcast
        - [ ] Episode
    - [x] Check-In
- [x] Watch
    - [x] Movie
    - [x] Series
        - [x] Episode
    - [ ] Cast
    - [x] Check-In


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
