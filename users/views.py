# views.py

from decouple import config
import os, json, re, requests, datetime as dt
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404, render
from .models import Roadmap
from datetime import timedelta
import math

OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
API_KEY            = config("OPENROUTER_API_KEY")


def index(request):
    return render(request, "index.html")


def generate_suggestions(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST expected")

    try:
        p          = json.loads(request.body)
        topic      = p["topic"].strip()
        week_hours = int(p["hours"])

        start = dt.date.fromisoformat(p["start_date"])
        end   = dt.date.fromisoformat(p["end_date"])
        if end < start:
            return HttpResponseBadRequest("end_date < start_date")
    except (KeyError, ValueError, json.JSONDecodeError):
        return HttpResponseBadRequest("Bad JSON")

    days_total  = (end - start).days
    total_hours  = int(week_hours/7 * days_total)

    prompt = (
        f"I want to learn {topic}. "
        f"I have {total_hours} in total for the project. "
        "The project will be separated into smaller ones for each subtopic."
        " I want 3 ideas as project names for the final project in a JSON format in the following way, DO NOT DEVIATE FROM THE GIVEN FORMAT NO EXTRA TEXT:"
        "{\"project_ideas\": [\"name_1\", \"name_2\", \"name_3\"]}"
    )

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type":  "application/json",
    }
    data = {
        "model":       "openai/gpt-4o-mini",
        "messages":    [{"role": "user", "content": prompt}],
        "max_tokens":  300,
        "temperature": 0.7,
    }

    try:
        r = requests.post(OPENROUTER_ENDPOINT, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"]

        print(raw)
        print('---------------')
        print(total_hours)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    ideas = []
    m = re.search(r'\{.*?\}', raw, re.S)
    if m:
        try:
            parsed = json.loads(m.group(0))
            ideas  = parsed.get("project_ideas", [])[:3]
        except json.JSONDecodeError:
            pass

    if not ideas:
        ideas = re.findall(r'"([^"]+)"', raw)[:3] or raw.strip().split("\n")[:3]

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
        start_date = dt.date.fromisoformat(request.POST["start_date"])
        end_date = dt.date.fromisoformat(request.POST["end_date"])
        project_idea = request.POST["selected_project"].strip()
    except (KeyError, ValueError):
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
    data    = {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000,
        "temperature": 0.8,
    }

    try:
        resp = requests.post(OPENROUTER_ENDPOINT, headers=headers, json=data, timeout=60)
        resp.raise_for_status()
        raw_json = resp.json()["choices"][0]["message"]["content"]

        print('----------------------------------------')
        print(raw_json)

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

    raw     = roadmap.raw_json
    topics  = []
    final   = {}

    try:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if not m:
            raise ValueError("JSON object not found in raw_json")

        parsed = json.loads(m.group(0))
        topics = parsed.get("topics", [])
        final  = parsed.get("final_project", {})
    except Exception as e:
        print("❌ Problem with raw_json:", e)
        print("RAW repr:", repr(raw)[:400])

    daily_quota = roadmap.week_hours / 7
    cur_date = roadmap.start_date

    for t in topics:
        need_h = t.get("hours", 0)
        days_needed = max(0, round(need_h / daily_quota))

        end_date = cur_date + timedelta(days=days_needed - 1)

        if end_date > roadmap.end_date:
            end_date = roadmap.end_date  # не выходим за конец
            days_needed = (end_date - cur_date).days + 1

        if days_needed == 0 :
            date_label = cur_date.strftime("%d %b")
        else:
            date_label = cur_date.strftime("%d %b")

        t["date_label"] = date_label
        t["daily_hours"] = round(daily_quota, 1)

        cur_date = end_date + timedelta(days=1)

        if cur_date > roadmap.end_date:
            break

    return render(request, "roadmap.html", {
        "roadmap": roadmap,
        "topics":  topics,
        "final":   final,
        "raw":     raw,
    })


def my_roadmaps(request):
    roadmaps = Roadmap.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "my_roadmaps.html", {"roadmaps": roadmaps})

def delete_roadmap(request, roadmap_id):
    roadmap = get_object_or_404(Roadmap, id=roadmap_id, user=request.user)
    roadmap.delete()
    return JsonResponse({"ok": True})
