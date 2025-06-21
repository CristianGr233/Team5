import uuid
from django.conf import settings
from django.db import models


class Roadmap(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    topic        = models.CharField(max_length=255)
    total_hours  = models.PositiveIntegerField()
    project_idea = models.CharField(max_length=255)
    raw_json     = models.TextField()
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic} – {self.project_idea}"
