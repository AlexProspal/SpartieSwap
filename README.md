# SpartieSwap

A campus borrowing and lending platform for students.

Students often need something for a couple of days - a calculator before an exam, a
charger, a tool, a lab coat - and buying it is a waste. Right now that happens over
group chats where posts get buried. SpartieSwap puts it in one place: someone lists an
item, someone else asks to borrow it for specific dates, the owner says yes or no, and
both sides can see where the exchange stands until the item comes back.

CSDS 393 Software Engineering, Summer 2026.
Alexander Prospal (Product Owner), Josef Broz (Scrum Master), Gina Cheng, Shenguo Wu.

## What it's built with

Django 5.2 on Python 3.13, Django templates with Bootstrap 5 for the pages, and
PostgreSQL 16 for the database. Login uses Django's built-in auth, restricted to
`@case.edu` addresses. GitHub Actions runs the tests on every pull request.

## Getting it running

You'll need Python 3.13 or newer and Docker Desktop.

```bash
git clone https://github.com/AlexProspal/SpartieSwap.git
cd SpartieSwap

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env               # Windows: copy .env.example .env

docker compose up -d               # starts Postgres on port 5432
python manage.py migrate
python manage.py runserver
```

That gets you the site at http://127.0.0.1:8000/. Sign up with any `@case.edu`
address - it doesn't send email, so you can make up whatever you want.

If you want to poke around the Django admin at `/admin/`, make yourself an account:

```bash
python manage.py createsuperuser
```

Docker only needs `docker compose up -d` the first time. After that the container
restarts with Docker Desktop, and `docker compose down` stops it if you want the port
back.

## Tests

```bash
python manage.py test
```

Run this before opening a pull request, since CI runs the same thing and will block the
merge if anything fails. There's also a style check:

```bash
ruff check .
```

## How the code is organized

```
config/       settings, root URLs, the home page view
accounts/     user model, the case.edu rule, signup and login
templates/    base layout and the pages
static/       our CSS
```

More apps get added as we pick up their stories:

- `listings` - creating items, browsing, item detail pages, managing your own listings
- `loans` - requests, approving and declining, pickup and return tracking
- `reviews` - ratings after a loan finishes

Anything configurable lives in environment variables, and `.env.example` lists all of
them with working defaults. The one worth knowing about is `CAMPUS_EMAIL_DOMAIN`, which
controls who's allowed to register.

## Working on it

Nothing goes straight to `main`. Branch off it, name the branch after what you're doing
(`feature/item-listings`, `bugfix/login-validation`, `docs/report-update`), and open a
pull request when you're ready.

In the PR, say what you changed, link the Issue it belongs to, and mention how you
tested it. Someone else on the team has to review it, and CI has to be green before it
merges. Once it's in, close the Issue and move the card to Done.

A story counts as finished when its acceptance criteria actually work, there are tests
covering it, CI passes, someone reviewed it, and the docs still match what the code
does.
