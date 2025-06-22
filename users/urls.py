from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path("generate-suggestions/", views.generate_suggestions, name="generate_suggestions"),
    path('create_roadmap/', views.create_roadmap, name='create_roadmap'),
    path('roadmap/<uuid:roadmap_id>/', views.roadmap_detail, name='roadmap_detail'),
    path("my-roadmaps/", views.my_roadmaps, name="my_roadmaps"),
    path("roadmap/<uuid:roadmap_id>/delete/", views.delete_roadmap, name="delete_roadmap"),
    path("roadmap/<uuid:roadmap_id>/add_to_calendar/<int:step_index>/", views.add_to_calendar, name="add_to_calendar"),
    path(
        'roadmap/<uuid:roadmap_id>/article/',
        views.get_or_generate_article,
        name='get_or_generate_article'
    ),
]