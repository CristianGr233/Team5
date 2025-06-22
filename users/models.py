import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField


class Roadmap(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    topic        = models.CharField(max_length=255)
    week_hours   = models.PositiveIntegerField(default=0)
    total_hours  = models.PositiveIntegerField(default=0)
    start_date   = models.DateField(default=timezone.now)
    end_date     = models.DateField(default=timezone.now)

    project_idea = models.CharField(max_length=255)
    raw_json     = models.TextField()

    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic} – {self.project_idea}"

class Article(models.Model):
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name='articles')
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    topic   = models.CharField(max_length=255)
    content = models.TextField()
    sources    = ArrayField(models.URLField(), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Article «{self.topic}» for {self.roadmap.topic}"