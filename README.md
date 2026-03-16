# Email Daemon

A Django-based email forwarding service that manages mailing lists for the cyphy.life domain. It monitors a Gmail inbox for incoming emails addressed to `@cyphy.life` aliases and automatically forwards them to all active subscribers.

## How It Works

1. Emails arrive at a Gmail inbox addressed to mailing list aliases (e.g., `msgs@cyphy.life`)
2. A background daemon polls Gmail IMAP every 60 seconds
3. When it finds an email matching a mailing list alias, it forwards it to all active subscribers
4. Forwarded emails preserve the original sender, threading, and attachments with a `[LISTNAME]` subject prefix
5. Users can subscribe/unsubscribe via a web interface with email confirmation

## Tech Stack

- **Python 3.9** / **Django 4.2**
- **Gunicorn** — WSGI server
- **Supervisor** — process manager (runs web server + email daemon)
- **SQLite** — database
- **Gmail IMAP/SMTP** — email sending and receiving
- **Docker** / **Docker Compose** — containerization
- **Bootstrap 5** — frontend

## Prerequisites

- Python 3.9+
- A Gmail account with [App Passwords](https://support.google.com/accounts/answer/185833) enabled (requires 2FA)
- Docker & Docker Compose (for containerized deployment)

## Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd email_daemon
```

### 2. Create a `.env` file

```bash
EMAIL_ADDRESS=your-gmail@gmail.com
EMAIL_PASSWORD=your-gmail-app-password
```

> **Note:** You must use a Gmail App Password, not your regular Gmail password.

### 3. Run with Docker (recommended)

```bash
docker-compose up --build
```

This will:
- Build the container
- Run database migrations
- Start Supervisor, which manages both the Django web server and the email daemon

The app will be available at `http://localhost:8081`.

### 4. Run manually (development)

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start the web server (terminal 1)
python manage.py runserver 8081

# Start the email daemon (terminal 2)
python manage.py run_email_daemon
```

## Project Structure

```
email_daemon/
├── emaildaemon/                # Django project config
│   ├── settings.py             # Main settings (IMAP/SMTP, CSRF, logging)
│   ├── urls.py                 # URL routing
│   └── wsgi.py                 # WSGI entry point
├── emails/                     # Main Django app
│   ├── models.py               # MailingList & Subscriber models
│   ├── views.py                # Subscribe/unsubscribe views
│   ├── forms.py                # Subscription forms
│   ├── email_daemon.py         # Email forwarding daemon
│   ├── utils.py                # JWT tokens, email utilities
│   ├── admin.py                # Django admin config
│   ├── management/commands/
│   │   └── run_email_daemon.py # Management command to start daemon
│   └── templates/emails/       # HTML templates
├── templates/
│   └── base.html               # Base template (Bootstrap)
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── supervisord.conf
└── entrypoint.sh
```

## Web Interface

| Route | Description |
|-------|-------------|
| `/` | Main page — subscribe, check subscriptions, unsubscribe |
| `/admin/` | Django admin — manage mailing lists and subscribers |
| `/test-email/` | Sends a test email to verify SMTP is working |
| `/unsubscribe/confirm/` | Handles unsubscribe confirmation links (JWT) |

## Models

**MailingList** — an alias like `msgs@cyphy.life` with a description.

**Subscriber** — an email address subscribed to one or more mailing lists, with an active/inactive status.

## Configuration

Key settings in `emaildaemon/settings.py`:

| Setting | Value |
|---------|-------|
| Port | `8081` |
| IMAP server | `imap.gmail.com` |
| SMTP server | `smtp.gmail.com:587` |
| Check interval | 60 seconds |
| JWT token expiry | 30 days |
| Gunicorn workers | 2 |
| Docker memory limit | 256MB |

## Managing Mailing Lists

Mailing lists are created through the Django admin at `/admin/`. Create a superuser first:

```bash
python manage.py createsuperuser
```

Then log in at `/admin/` and add mailing lists with their `@cyphy.life` aliases.
