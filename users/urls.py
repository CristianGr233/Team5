from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path("generate-suggestions/", views.generate_suggestions, name="generate_suggestions"),
]