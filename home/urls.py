# home/urls.py
from django.urls import path
from . import views_ops

urlpatterns = [
    path("ops/", views_ops.ops_public_lookup, name="ops_public_lookup"),

    # Manager page (two names so templates don’t break)
    path("ops/manage/", views_ops.manager_lookup, name="ops_dashboard"),
    path("ops/manage/", views_ops.manager_lookup, name="ops_manager_lookup"),
    path("ops/history/", views_ops.manager_history_lookup, name="ops_history"),

    # Actions
    path("ops/routes/create/", views_ops.ops_route_create, name="ops_route_create"),
    path("ops/routes/discontinue/", views_ops.ops_route_discontinue, name="ops_route_discontinue"),
    path("ops/journeys/<int:pk>/quick-update/", views_ops.ops_journey_quick_update, name="ops_journey_quick_update"),
]
