from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path("generate-suggestions/", views.generate_suggestions, name="generate_suggestions"),
    path('create_roadmap/', views.create_roadmap, name='create_roadmap'),
    path('roadmap/<uuid:roadmap_id>/', views.roadmap_detail, name='roadmap_detail'),
]