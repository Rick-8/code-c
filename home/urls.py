# home/urls.py
from django.urls import path
from . import views_ops

urlpatterns = [
    # Public
    path("ops/", views_ops.ops_public_lookup, name="ops_public_lookup"),

    # Manager (two names so templates don't break)
    path("ops/manage/", views_ops.manager_lookup, name="ops_dashboard"),
    path("ops/manage/", views_ops.manager_lookup, name="ops_manager_lookup"),

    # Manager history
    path("ops/history/", views_ops.manager_history_lookup, name="ops_history"),

    # Actions
    path("ops/routes/create/", views_ops.ops_route_create, name="ops_route_create"),
    path("ops/routes/discontinue/", views_ops.ops_route_discontinue, name="ops_route_discontinue"),
    path("ops/journeys/<int:pk>/quick-update/", views_ops.ops_journey_quick_update, name="ops_journey_quick_update"),

    # Ops Hub (journal + todos)
    path("ops/hub/", views_ops.ops_hub, name="ops_hub"),
    path("ops/journal/autosave/", views_ops.ops_journal_autosave, name="ops_journal_autosave"),
    path("ops/journal/history/", views_ops.ops_journal_history, name="ops_journal_history"),
    path("ops/todo/add/", views_ops.ops_todo_add, name="ops_todo_add"),
    path("ops/todo/<int:pk>/complete/", views_ops.ops_todo_complete, name="ops_todo_complete"),
    path("ops/todo/history/", views_ops.ops_todo_history, name="ops_todo_history"),
]
