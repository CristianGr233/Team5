# views.py

from decouple import config
import os, json, re, requests, datetime as dt
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render

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

    return JsonResponse({"ideas": ideas})
