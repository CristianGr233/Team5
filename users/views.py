from decouple import config
import os
import json
import re
import requests

from django.conf import settings
from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse, HttpResponseBadRequest

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from .models import Roadmap

from datetime import date, datetime, time, timedelta
import math

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = config("OPENROUTER_API_KEY")


def index(request):
    return render(request, "index.html")


def generate_suggestions(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST expected")

    try:
        p = json.loads(request.body)
        topic = p.get("topic", "").strip()
        week_hours = int(p.get("hours", 0))
        start = date.fromisoformat(p.get("start_date"))
        end = date.fromisoformat(p.get("end_date"))
        if end < start:
            return HttpResponseBadRequest("end_date < start_date")
    except Exception:
        return HttpResponseBadRequest("Bad JSON or data")

    days_total = (end - start).days
    total_hours = int(week_hours / 7 * days_total)

    prompt = (
        f"I want to learn {topic}. "
        f"I have {total_hours} in total for the project. "
        "The project will be separated into smaller ones for each subtopic."
        " I want 3 ideas as project names for the final project in a JSON format in the following way, DO NOT DEVIATE FROM THE GIVEN FORMAT NO EXTRA TEXT:"
        '{"project_ideas": ["name_1", "name_2", "name_3"]}'
    )

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
        "temperature": 0.7,
    }

    try:
        r = requests.post(OPENROUTER_ENDPOINT, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    ideas = []
    m = re.search(r"\{.*?\}", raw, re.S)
    if m:
        try:
            parsed = json.loads(m.group(0))
            ideas = parsed.get("project_ideas", [])[:3]
        except json.JSONDecodeError:
            pass
    if not ideas:
        ideas = re.findall(r'"([^"]+)"', raw)[:3]

    return JsonResponse({
        "ideas": ideas,
        "total_hours": total_hours,
        "topic": topic
    })


def create_roadmap(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST expected")

    try:
        topic = request.POST["topic"].strip()
        week_hours = int(request.POST["week_hours"])
        total_hours = int(request.POST["total_hours"])
        start_date = date.fromisoformat(request.POST["start_date"])
        end_date = date.fromisoformat(request.POST["end_date"])
        project_idea = request.POST["selected_project"].strip()
    except Exception:
        return HttpResponseBadRequest("Bad data")

    prompt = (
        f"I want to learn <{topic}>. "
        f"I have <{total_hours}> hours. "
        "I need a road map for this course that will contain topics I need to learn for this course. "
        "For each topic I will need amount of hours I need to spent on it and list of few subtopics, that I need to go over. "
        "Each topic should contribute to the final project by parts, including this topic in the project. "
        "The project part should include a task for the project, that would include the topic user just went over, "
        "building a final project that combines all the knowledge. "
        f"The project idea is: <{project_idea}>. "
        "Please provide output as JSON file I can download. "
        "The JSON file should follow the following structure NO EXTRA TEXT DO NOT FORGET FINAL PROJECT PART: "
        '{ "total_hours":"", "topics":[ { "name": "", "hours": 0, "subtopics": [ { "name": "", "description": "" } ], "project_part": "" } ], '
        '"final_project": { "name": "", "description": "" } }'
    )

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000,
        "temperature": 0.8,
    }

    try:
        resp = requests.post(OPENROUTER_ENDPOINT, headers=headers, json=data, timeout=60)
        resp.raise_for_status()
        raw_json = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    roadmap = Roadmap.objects.create(
        user=request.user,
        topic=topic,
        week_hours=week_hours,
        total_hours=total_hours,
        start_date=start_date,
        end_date=end_date,
        project_idea=project_idea,
        raw_json=raw_json,
    )
    return redirect("roadmap_detail", roadmap_id=roadmap.id)


def roadmap_detail(request, roadmap_id):
    roadmap = get_object_or_404(Roadmap, id=roadmap_id, user=request.user)
    raw = roadmap.raw_json
    topics = []
    final = {}

    try:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        parsed = json.loads(m.group(0)) if m else {}
        topics = parsed.get("topics", [])
        final = parsed.get("final_project", {})
    except Exception:
        pass

    daily_quota = roadmap.week_hours / 7
    cur_date = roadmap.start_date
    schedule = []
    for t in topics:
        need_h = t.get("hours", 0)
        days_needed = max(1, round(need_h / daily_quota))
        end_date = cur_date + timedelta(days=days_needed - 1)
        if end_date > roadmap.end_date:
            end_date = roadmap.end_date
            days_needed = (end_date - cur_date).days + 1
        t["start_date"] = cur_date
        t["end_date"] = end_date
        t["date_label"] = cur_date.strftime("%d %b")
        t["daily_hours"] = round(daily_quota, 1)
        cur_date = end_date + timedelta(days=1)
        schedule.append(t)
        if cur_date > roadmap.end_date:
            break

    return render(request, "roadmap.html", {
        "roadmap": roadmap,
        "topics": schedule,
        "final": final,
        "raw": raw,
    })


def my_roadmaps(request):
    roadmaps = Roadmap.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "my_roadmaps.html", {"roadmaps": roadmaps})


def delete_roadmap(request, roadmap_id):
    roadmap = get_object_or_404(Roadmap, id=roadmap_id, user=request.user)
    roadmap.delete()
    return JsonResponse({"ok": True})


def add_to_calendar(request, roadmap_id, step_index):
    # 1. Найти Roadmap
    roadmap = get_object_or_404(Roadmap, id=roadmap_id, user=request.user)

    # 2. Достать social_auth запись Google OAuth2
    try:
        sa = request.user.social_auth.get(provider='google-oauth2')
    except request.user.social_auth.model.DoesNotExist:
        return HttpResponseBadRequest("Google OAuth not configured for this user")

    extra = sa.extra_data

    # 3. Если нет refresh_token — заставляем пользователя пройти consent заново
    if not extra.get('refresh_token'):
        request.session['post_oauth_redirect'] = request.path
        return redirect('social:begin', backend='google-oauth2')

    # 4. Собираем Credentials
    creds = Credentials(
        token=extra.get('access_token'),
        refresh_token=extra.get('refresh_token'),
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
        client_secret=settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
        scopes=['https://www.googleapis.com/auth/calendar'],
    )

    # 5. Если access_token истёк — обновляем через правильный Request
    if creds.expired:
        try:
            creds.refresh(Request())
        except Exception:
            request.session['post_oauth_redirect'] = request.path
            return redirect('social:begin', backend='google-oauth2')
        sa.extra_data['access_token'] = creds.token
        sa.extra_data['expires_in'] = int((creds.expiry - datetime.utcnow()).total_seconds())
        sa.save()

    # 6. Парсим roadmap.raw_json и вычисляем даты для шагов
    raw = roadmap.raw_json
    data = json.loads(re.search(r'\{.*\}', raw, re.S).group(0))
    topics = data.get('topics', [])

    daily_quota = roadmap.week_hours / 7
    current = roadmap.start_date
    enriched = []
    for t in topics:
        hours = t.get('hours', 0)
        days = max(1, round(hours / daily_quota))
        enriched.append({'name': t['name'], 'start': current, 'hours': hours})
        current = current + timedelta(days=days)
        if current > roadmap.end_date:
            break

    try:
        step = enriched[int(step_index)]
    except Exception:
        return HttpResponseBadRequest("Step not found")

    # 7. Формируем событие и отправляем в Google Calendar API
    start_dt = datetime.combine(step['start'], time(17, 0))
    end_dt = start_dt + timedelta(hours=step['hours'])
    event = {
        'summary': f"{roadmap.topic}",
        'description': f"Roadmap step '" + step['name'] + "', " + str(step['hours']) + "h.",
        'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Europe/Chisinau'},
        'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Europe/Chisinau'},
    }

    service = build('calendar', 'v3', credentials=creds)
    created = service.events().insert(calendarId='primary', body=event).execute()

    # 8. Возвращаем результаты
    return redirect('roadmap_detail', roadmap_id=roadmap.id)
