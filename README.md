# Team5

**AI Roadmap Builder Tool**
A Django web application that allows users to generate personalized learning roadmaps using an LLM (OpenRouter GPT-4o-mini). Each roadmap can be saved, and individual topics from the roadmap can be added to the user’s Google Calendar as all-day events.

---

## Features

* User authentication via Google (social-auth-app-django).
* Prompt-based roadmap generation using GPT-4o-mini through OpenRouter.
* Storage of generated roadmaps and topics in a PostgreSQL database.
* Per-topic calendar event creation with a single click, using Google Calendar API.
* Responsive front-end styled with Tailwind CSS and Alpine.js for interactivity.

---

## Prerequisites

* Python 3.10 or newer
* pip (package installer)
* virtualenv (optional but recommended)
* A Google Cloud project with OAuth 2.0 credentials and Calendar API enabled
* OpenRouter API key

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/roadmap-calendar.git
cd roadmap-calendar
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate    # macOS/Linux
venv\Scripts\activate     # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment variables

Create a `.env` file in the project root with the following values:

```ini
DJANGO_SECRET_KEY=your_django_secret_key
DATABASE_URL=postgres://user:password@localhost:5432/yourdb  # or leave blank for SQLite
OPENROUTER_ENDPOINT=https://openrouter.ai/api/v1/chat/completions
API_KEY=your_openrouter_api_key
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_API_KEY=your_google_api_key
```

### 5. Database setup

Apply migrations:

```bash
python manage.py migrate
```

(Optional) Create a superuser:

```bash
python manage.py createsuperuser
```

### 6. Google Cloud configuration

1. In Google Cloud Console, create or select your project.
2. Enable the **Google Calendar API** under **APIs & Services → Library**.
3. In **APIs & Services → Credentials**, create an **OAuth 2.0 Client ID** (Web application).

   * **Authorized JavaScript origins**:

     ```
     http://localhost:8000
     http://127.0.0.1:8000
     ```
   * **Authorized redirect URIs**:

     ```
     http://localhost:8000/complete/google-oauth2/
     ```
4. Add the OAuth Client ID and Client Secret to your `.env`.

### 7. Run the development server

```bash
python manage.py runserver
```

Open your browser at `http://localhost:8000`.

---

## Usage

1. Log in via Google.
2. On the home page, fill out the form to generate a roadmap:

   * Topic
   * Weekly hours
   * Start and end dates
   * Project idea
3. Submit and view your roadmap detail page.
4. Click **Add to calendar** next to any topic to insert an all-day event into your Google Calendar.

---

## Acknowledgments

* Built with Django, social-auth-app-django, Tailwind CSS, Alpine.js.
* API powered by OpenRouter GPT-4o-mini.
* Calendar integration via Google Calendar JavaScript API.
