# LuvDB

Built with Django and Bootstrap.

## Features / Roadmap (subject to change)

- [x] User Profile
- [x] Activity Feed
    - [x] Follow/Unfollow
- [x] Write
    - [x] Say (Twitter-like)
    - [x] Pin (Hacker News / Pinboard-like)
    - [x] Post (Blog-like)
    - [x] Repost (Retweet-like)
    - [x] Comment 
    - [ ] Review
    - [ ] Thought
    - [ ] Quote
- [ ] Play
    - [ ] Game
        - [ ] Edition (Remake / DLC)
        - [ ] Publisher
        - [ ] Series
    - [ ] Person (Developer / Publisher)
- [ ] Read
    - [ ] Book
        - [ ] Edition (Reprint / Translation / Audiobook)
        - [ ] Publisher
        - [ ] Series
    - [ ] Article
        - [ ] Journal
        - [ ] Magazine
    - [ ] Person (Author / Translator / Editor / Designer / Narrator)
- [ ] Watch
    - [ ] Movie
    - [ ] Series
        - [ ] Season
            - [ ] Episode
    - [ ] Person (Actor / Director / Producer / Writer)
- [ ] Listen
    - [ ] Album
        - [ ] Song
    - [ ] Podcast
        - [ ] Episode
    - [ ] Person (Composer / Lyricist / Musician / Singer / Designer)

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
touch .env
python -c 'from django.core.management.utils import get_random_secret_key; print("SECRET_KEY="+get_random_secret_key())' > .env
echo "DEBUG=True" >> .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
