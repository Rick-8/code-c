# home/views_ops.py
from __future__ import annotations
from datetime import timedelta
from django.db.models import Count
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from .models import OpsJourney, OpsRoute, OpsChangeLog
from .permissions import user_can_manage_ops

from django.http import JsonResponse
from .models import OpsDailyJournal
from .models import OpsDailyJournal, OpsDailyJournalRevision, OpsTodoItem


# =========================================================
# Helpers
# =========================================================


def _ensure_today_journeys(user) -> timezone.datetime.date:
    """
    Ensure there is exactly one 'today' OpsJourney row for each ACTIVE route.
    This makes new routes instantly appear on both manager + public boards.
    """
    today = timezone.localdate()

    active_routes = OpsRoute.objects.filter(is_active=True).order_by("code")

    with transaction.atomic():
        for route in active_routes:
            OpsJourney.objects.get_or_create(
                route=route,
                service_date=today,
                defaults={
                    "status": OpsJourney.STATUS_ON_TIME,
                    "delay_minutes": None,
                    "reason": "",
                    "updated_by": user if getattr(user, "is_authenticated", False) else None,
                },
            )

    return today


def _attach_last_journey(routes):
    """
    For each route in 'routes', attach route.last_journey = most recent OpsJourney (or None).
    Keeps templates simple (no dict gymnastics).
    """
    for r in routes:
        r.last_journey = (
            OpsJourney.objects.filter(route=r)
            .order_by("-service_date", "-updated_at", "-pk")
            .first()
        )
    return routes


# =========================================================
# Public board
# =========================================================

def ops_public_lookup(request: HttpRequest) -> HttpResponse:
    """
    Public board shows today's services for all ACTIVE routes.
    If a route exists and is active, it WILL appear (default on-time until updated).
    """
    today = timezone.localdate()
    weekend = today.weekday() >= 5  # 5=Sat, 6=Sun

    if weekend:
        return render(
            request,
            "home/ops/public_lookup.html",
            {
                "weekend": True,
                "journeys": [],
                "today": today,
                "can_manage": user_can_manage_ops(request.user),
            },
        )

    _ensure_today_journeys(request.user)

    journeys = (
        OpsJourney.objects.select_related("route")
        .filter(route__is_active=True, service_date=today)
        .order_by("route__code")
    )

    return render(
        request,
        "home/ops/public_lookup.html",
        {
            "weekend": False,
            "journeys": journeys,
            "today": today,
            "can_manage": user_can_manage_ops(request.user),
        },
    )


# =========================================================
# Manager board
# =========================================================

@login_required
def manager_lookup(request: HttpRequest) -> HttpResponse:
    if not user_can_manage_ops(request.user):
        messages.error(request, "You do not have permission to access Live Ops Manager.")
        return redirect("home")

    today = _ensure_today_journeys(request.user)

    # Active (today) journeys
    journeys = (
        OpsJourney.objects.select_related("route")
        .filter(route__is_active=True, service_date=today)
        .order_by("route__code")
    )

    # Discontinued routes (do NOT create journeys for these)
    discontinued_routes = OpsRoute.objects.filter(is_active=False).order_by("code")
    discontinued_routes = _attach_last_journey(discontinued_routes)

    return render(
        request,
        "home/ops/manager_lookup.html",
        {
            "journeys": journeys,
            "today": today,
            "can_manage": True,  # important so History button displays
            "discontinued_routes": discontinued_routes,
        },
    )


# =========================================================
# Create route
# =========================================================

@require_POST
@login_required
def ops_route_create(request: HttpRequest) -> HttpResponse:
    """
    Create a new OpsRoute and immediately create today's journey row for it
    so it appears on the public board instantly.
    Also writes an audit log entry (append-only).
    """
    if not user_can_manage_ops(request.user):
        messages.error(request, "You do not have permission to create routes.")
        return redirect("ops_dashboard")

    code = (request.POST.get("code") or "").strip().upper()
    name = (request.POST.get("name") or "").strip()
    origin = (request.POST.get("origin") or "").strip()
    destination = (request.POST.get("destination") or "").strip()

    if not all([code, name, origin, destination]):
        messages.error(request, "Please complete all route fields.")
        return redirect("ops_dashboard")

    today = timezone.localdate()

    try:
        with transaction.atomic():
            route = OpsRoute.objects.create(
                code=code,
                name=name,
                origin=origin,
                destination=destination,
                is_active=True,
            )

            journey, _ = OpsJourney.objects.get_or_create(
                route=route,
                service_date=today,
                defaults={
                    "status": OpsJourney.STATUS_ON_TIME,
                    "delay_minutes": None,
                    "reason": "",
                    "updated_by": request.user,
                },
            )

            OpsChangeLog.objects.create(
                action=OpsChangeLog.ACTION_ROUTE_CREATED,
                route=route,
                journey=journey,
                changed_by=request.user,
                note="Route created in manager panel.",
                new_status=journey.status,
                new_delay_minutes=journey.delay_minutes,
                new_reason=journey.reason,
            )

    except IntegrityError:
        messages.error(request, f"Route code '{code}' already exists. Please choose a different code.")
        return redirect("ops_dashboard")

    messages.success(request, f"Route {code} created and is now live for today.")
    return redirect("ops_dashboard")


# =========================================================
# Discontinue route (soft stop, no deletion)
# =========================================================

@require_POST
@login_required
def ops_route_discontinue(request: HttpRequest) -> HttpResponse:
    if not user_can_manage_ops(request.user):
        messages.error(request, "You do not have permission to manage Live Ops.")
        return redirect("ops_dashboard")

    route_id = request.POST.get("route_id")
    route = get_object_or_404(OpsRoute, pk=route_id)

    route.is_active = False
    route.save(update_fields=["is_active"])

    OpsChangeLog.objects.create(
        action=OpsChangeLog.ACTION_ROUTE_DISCONTINUED,
        route=route,
        journey=None,
        changed_by=request.user,
        note="Route discontinued in manager panel.",
    )

    messages.success(request, f"Route discontinued: {route.code} – it will no longer appear on the live board.")
    return redirect("ops_dashboard")


# =========================================================
# Quick update journey status
# =========================================================

@require_POST
@login_required
def ops_journey_quick_update(request: HttpRequest, pk: int) -> HttpResponse:
    if not user_can_manage_ops(request.user):
        messages.error(request, "You do not have permission to manage Live Ops.")
        return redirect("ops_dashboard")

    j = get_object_or_404(OpsJourney.objects.select_related("route"), pk=pk)

    old_status = j.status
    old_delay = j.delay_minutes
    old_reason = j.reason

    status = (request.POST.get("status") or "").strip()
    delay_raw = (request.POST.get("delay_minutes") or "").strip()
    reason = (request.POST.get("reason") or "").strip()

    j.status = status or OpsJourney.STATUS_ON_TIME

    if delay_raw == "":
        j.delay_minutes = None
    else:
        try:
            j.delay_minutes = int(delay_raw)
        except ValueError:
            messages.error(request, "Delay minutes must be a number.")
            return redirect("ops_dashboard")

    j.reason = reason
    j.updated_by = request.user

    try:
        j.full_clean()
    except ValidationError as e:
        messages.error(request, "Could not save update: " + " ".join(e.messages))
        return redirect("ops_dashboard")

    j.save()

    OpsChangeLog.objects.create(
        action=OpsChangeLog.ACTION_JOURNEY_UPDATED,
        route=j.route,
        journey=j,
        changed_by=request.user,
        note="Status updated in manager panel.",
        old_status=old_status,
        old_delay_minutes=old_delay,
        old_reason=old_reason,
        new_status=j.status,
        new_delay_minutes=j.delay_minutes,
        new_reason=j.reason,
    )

    messages.success(request, f"Updated: {j.route.code} – {j.get_status_display()}")
    return redirect("ops_dashboard")


# =========================================================
# Manager history/audit log
# =========================================================

@login_required
def manager_history_lookup(request: HttpRequest) -> HttpResponse:
    """
    Manager history/audit log.
    Filters:
      - date_from / date_to (journey.service_date where possible, else created_at date)
      - route (by route id)
      - q (text search across route code/name + note + action)
    Shows discontinued routes too.
    """
    if not user_can_manage_ops(request.user):
        messages.error(request, "You do not have permission to access Live Ops history.")
        return redirect("home")

    date_from_raw = (request.GET.get("date_from") or "").strip()
    date_to_raw = (request.GET.get("date_to") or "").strip()
    route_id = (request.GET.get("route") or "").strip()
    q = (request.GET.get("q") or "").strip()

    date_from = parse_date(date_from_raw) if date_from_raw else None
    date_to = parse_date(date_to_raw) if date_to_raw else None

    if not date_from and not date_to:
        date_to = timezone.localdate()
        date_from = date_to - timedelta(days=7)

    logs = (
        OpsChangeLog.objects.select_related("route", "journey", "changed_by")
        .all()
        .order_by("-created_at", "-pk")
    )

    # Date filtering:
    # Prefer journey.service_date; fallback to created_at for route-only events.
    if date_from and date_to:
        logs = logs.filter(
            Q(journey__service_date__range=(date_from, date_to))
            | Q(journey__isnull=True, created_at__date__range=(date_from, date_to))
        )
    elif date_from:
        logs = logs.filter(
            Q(journey__service_date__gte=date_from)
            | Q(journey__isnull=True, created_at__date__gte=date_from)
        )
    elif date_to:
        logs = logs.filter(
            Q(journey__service_date__lte=date_to)
            | Q(journey__isnull=True, created_at__date__lte=date_to)
        )

    if route_id:
        logs = logs.filter(route_id=route_id)

    if q:
        logs = logs.filter(
            Q(action__icontains=q)
            | Q(note__icontains=q)
            | Q(route__code__icontains=q)
            | Q(route__name__icontains=q)
            | Q(route__origin__icontains=q)
            | Q(route__destination__icontains=q)
        )

    routes = OpsRoute.objects.all().order_by("code")

    paginator = Paginator(logs, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "home/ops/manager_history_lookup.html",
        {
            "routes": routes,
            "page_obj": page_obj,
            "date_from": date_from,
            "date_to": date_to,
            "route_id": route_id,
            "q": q,
            "can_manage": True,
        },
    )


@login_required
def ops_hub(request):
    today = timezone.localdate()

    journal, _ = OpsDailyJournal.objects.get_or_create(
        user=request.user,
        entry_date=today,
        defaults={"content": ""},
    )

    todos = OpsTodoItem.objects.filter(
        user=request.user,
        is_done=False
    ).order_by("-created_at")

    return render(request, "home/ops/ops_hub.html", {
        "today": today,
        "journal": journal,
        "todos": todos,
    })


@require_POST
@login_required
def ops_journal_autosave(request):
    today = timezone.localdate()

    # Accept either JSON (fetch) or form-encoded POST
    content = ""
    if request.content_type and "application/json" in request.content_type:
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            payload = {}
        content = payload.get("content", "")
    else:
        content = request.POST.get("content", "")

    # IMPORTANT: do NOT .strip() here (prevents accidental “empty saves”)
    with transaction.atomic():
        journal, _ = OpsDailyJournal.objects.select_for_update().get_or_create(
            user=request.user,
            entry_date=today,
            defaults={"content": ""},
        )

        # If the browser posts nothing, don't nuke existing content
        # (extra safety net)
        if content is None:
            content = ""
        journal.content = content
        journal.save(update_fields=["content", "updated_at"])

        OpsDailyJournalRevision.objects.create(
            journal=journal,
            saved_by=request.user,
            content_snapshot=content,
        )

    return JsonResponse({
        "ok": True,
        "updated_at": journal.updated_at.isoformat(),
    })


@login_required
def ops_journal_history(request):
    """
    Journal history for the logged-in user.
    Lists daily entries, with optional search, paginated.
    """
    q = (request.GET.get("q") or "").strip()

    journals = (
        OpsDailyJournal.objects
        .filter(user=request.user)
        .annotate(rev_count=Count("revisions"))
        .order_by("-entry_date", "-updated_at")
    )

    if q:
        journals = journals.filter(content__icontains=q)

    paginator = Paginator(journals, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "home/ops/ops_journal_history.html",
        {
            "page_obj": page_obj,
            "q": q,
        },
    )


@login_required
def ops_todo_history(request):
    todos = (
        OpsTodoItem.objects
        .filter(user=request.user, is_done=True)
        .order_by("-done_at", "-updated_at")
    )

    paginator = Paginator(todos, 30)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "home/ops/ops_todo_history.html", {
        "page_obj": page_obj,
    })


@require_POST
@login_required
def ops_todo_add(request):
    title = (request.POST.get("title") or "").strip()

    if not title:
        messages.error(request, "Please enter a to-do item.")
        return redirect("ops_hub")

    # store uppercase so everything stays consistent everywhere
    OpsTodoItem.objects.create(
        user=request.user,
        title=title[:200].upper(),
    )

    return redirect("ops_hub")


@require_POST
@login_required
def ops_todo_complete(request, pk: int):
    todo = get_object_or_404(OpsTodoItem, pk=pk, user=request.user, is_done=False)

    todo.is_done = True
    todo.done_at = timezone.now()
    todo.save(update_fields=["is_done", "done_at", "updated_at"])

    messages.success(request, "To-do marked as DONE.")
    return redirect("ops_hub")
