from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from django.db.models import Count
from .models import Investigation, InvestigationLog
from django.http import HttpResponseForbidden

from .models import Interaction, InteractionAssignmentLog
from .forms import InteractionForm

User = get_user_model()


def is_manager(user):
    return user.is_authenticated and user.is_superuser


# ─────────────────────────────────────────────────────
# CREATE INTERACTION
# ─────────────────────────────────────────────────────
@login_required
def create_interaction(request):
    if request.method == "POST":
        form = InteractionForm(request.POST)
        if form.is_valid():
            interaction = form.save(commit=False)
            interaction.logged_by = request.user
            interaction.save()
            return redirect("qms_create")
    else:
        form = InteractionForm()

    return render(request, "qms/create_interaction.html", {"form": form})


# ─────────────────────────────────────────────────────
# MANAGER LIST VIEW
# ─────────────────────────────────────────────────────
@user_passes_test(is_manager)
def qms_manager_list(request):
    interactions = Interaction.objects.all().order_by("-logged_at")

    status = request.GET.get("status")
    interaction_type = request.GET.get("type")
    service_line = request.GET.get("service")

    if status:
        interactions = interactions.filter(status=status)
    if interaction_type:
        interactions = interactions.filter(interaction_type=interaction_type)
    if service_line:
        interactions = interactions.filter(service_line=service_line)

    return render(
        request,
        "qms/manager_list.html",
        {
            "interactions": interactions,
            "status_choices": Interaction.STATUS_CHOICES,
            "type_choices": Interaction.INTERACTION_TYPE_CHOICES,
            "service_choices": Interaction.SERVICE_LINE_CHOICES,
            "current_status": status,
            "current_type": interaction_type,
            "current_service": service_line,
        },
    )


# ─────────────────────────────────────────────────────
# SLIDE-IN PANEL CONTENT (AJAX)
# ─────────────────────────────────────────────────────
@user_passes_test(is_manager)
def qms_interaction_panel(request, pk):
    interaction = get_object_or_404(Interaction, pk=pk)

    staff_users = User.objects.filter(
        is_active=True,
        is_staff=True
    ).order_by("first_name", "last_name")

    return render(
        request,
        "qms/_interaction_panel_content.html",
        {
            "interaction": interaction,
            "staff_users": staff_users,
        }
    )


# ─────────────────────────────────────────────────────
# UPDATE INTERACTION (ASSIGN / REASSIGN / CLOSE)
# ─────────────────────────────────────────────────────
@staff_member_required
def update_interaction(request, pk):
    interaction = get_object_or_404(Interaction, pk=pk)

    if request.method == "POST":
        new_status = request.POST.get("status")
        manager_notes = request.POST.get("manager_notes", "").strip()
        new_assigned_to_id = request.POST.get("assigned_to") or None
        reassignment_reason = request.POST.get("reassignment_reason", "").strip()

        previous_assignee = interaction.assigned_to
        new_assignee = None

        if new_assigned_to_id:
            new_assignee = get_object_or_404(User, pk=new_assigned_to_id)

        # ─────────────────────────────────────────────
        # GUARD RAILS (ISO CONTROL)
        # ─────────────────────────────────────────────

        # Prevent reassignment once closed
        if interaction.status == "closed" and previous_assignee != new_assignee:
            messages.error(
                request,
                "Closed interactions cannot be reassigned."
            )
            return redirect("qms_manager_list")

        # Prevent closing unless assigned + notes exist
        if new_status == "closed":
            if not new_assignee and not previous_assignee:
                messages.error(
                    request,
                    "You must assign this interaction before closing it."
                )
                return redirect("qms_manager_list")

            if not manager_notes:
                messages.error(
                    request,
                    "Manager notes are required before closing an interaction."
                )
                return redirect("qms_manager_list")

        # ─────────────────────────────────────────────
        # ASSIGNMENT / REASSIGNMENT LOGGING
        # ─────────────────────────────────────────────
        if previous_assignee != new_assignee:
            InteractionAssignmentLog.objects.create(
                interaction=interaction,
                previous_assignee=previous_assignee,
                new_assignee=new_assignee,
                changed_by=request.user,
                reason=reassignment_reason if previous_assignee else ""
            )

            interaction.assigned_to = new_assignee

            # ─────────────────────────────────────────
            # EMAIL NOTIFICATION
            # ─────────────────────────────────────────
            if new_assignee and new_assignee.email:
                subject = "QMS Interaction Assigned"
                if previous_assignee:
                    subject = "QMS Interaction Reassigned"

                message = f"""
Hello {new_assignee.get_full_name() or new_assignee.username},

A Quality Management System interaction has been assigned to you.

Type: {interaction.get_interaction_type_display()}
Service: {interaction.get_service_line_display()}
Severity: {interaction.get_severity_display()}

Assigned by: {request.user.get_full_name() or request.user.username}
Logged: {interaction.logged_at:%d %b %Y %H:%M}
"""

                if previous_assignee:
                    message += f"""

Previously assigned to:
{previous_assignee.get_full_name() or previous_assignee.username}

Reason for reassignment:
{reassignment_reason}
"""

                message += """

Please log in to the system to review and action this item.

— Cozy Coaches QMS
"""

                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[new_assignee.email],
                    fail_silently=True,
                )

        # ─────────────────────────────────────────────
        # STATUS & NOTES
        # ─────────────────────────────────────────────
        interaction.status = new_status
        interaction.manager_notes = manager_notes

        if new_status == "closed" and interaction.closed_at is None:
            interaction.closed_at = timezone.now()

        interaction.save()
        messages.success(request, "Interaction updated successfully.")

    return redirect("qms_manager_list")


@user_passes_test(is_manager)
def investigation_dashboard(request):
    """
    Manager control dashboard for all staff investigations.
    High-level oversight for ISO 9001 compliance.
    """

    # TEMP: once Investigation model exists, replace Interaction below
    # with Investigation.objects.all()

    investigations = Interaction.objects.filter(
        interaction_type="incident"
    ).order_by("-logged_at")

    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)

    # ── KPI CALCULATIONS ─────────────────────────────────────
    kpi = {
        "open": investigations.filter(status__in=["open", "in_progress"]).count(),
        "awaiting": investigations.filter(
            assigned_to__isnull=False,
            status="open"
        ).count(),
        "overdue": investigations.filter(
            status="open",
            logged_at__lt=now - timedelta(days=7)
        ).count(),
        "closed": investigations.filter(
            status="closed",
            closed_at__gte=thirty_days_ago
        ).count(),
    }

    # ── ACTION REQUIRED QUEUE ────────────────────────────────
    action_required = investigations.filter(
        status="open"
    ).order_by("logged_at")[:20]

    context = {
        "kpi": kpi,
        "action_required": action_required,
    }

    return render(
        request,
        "qms/investigation_dashboard.html",
        context
    )


def is_manager(user):
    return user.is_authenticated and user.is_superuser


@user_passes_test(is_manager)
def investigation_dashboard_redirect(request):
    return redirect("investigation_dashboard")


@user_passes_test(is_manager)
def investigation_dashboard(request):
    now = timezone.now()

    investigations = Investigation.objects.select_related(
        "staff_member"
    ).all()

    kpi = {
        "open": investigations.filter(status="open").count(),
        "awaiting": investigations.filter(status="awaiting_response").count(),
        "overdue": investigations.filter(
            status="awaiting_response",
            created_at__lt=now - timezone.timedelta(days=7)
        ).count(),
        "closed": investigations.filter(
            status="closed",
            closed_at__gte=now - timezone.timedelta(days=30)
        ).count(),
    }

    action_required = investigations.filter(
        status__in=["open", "awaiting_response"]
    ).order_by("created_at")

    return render(
        request,
        "qms/investigation_dashboard.html",
        {
            "kpi": kpi,
            "action_required": action_required,
        },
    )


@user_passes_test(is_manager)
def investigation_create(request):
    staff_users = User.objects.filter(
        is_active=True,
        is_staff=True
    ).order_by("first_name", "last_name")

    if request.method == "POST":
        staff_id = request.POST.get("staff_member")
        reason = request.POST.get("reason")

        staff_member = None
        if staff_id:
            staff_member = get_object_or_404(User, pk=staff_id)

        investigation = Investigation.objects.create(
            staff_member=staff_member,
            reason=reason,
            created_by=request.user,
        )

        # Audit log (ISO gold)
        InvestigationLog.objects.create(
            investigation=investigation,
            event_type="created",
            performed_by=request.user,
            notes="Investigation case created",
        )

        messages.success(
            request,
            f"Investigation {investigation.case_number} created successfully."
        )

        return redirect("investigation_dashboard")

    return render(
        request,
        "qms/investigation_create.html",
        {
            "staff_users": staff_users,
        }
    )


@user_passes_test(lambda u: u.is_superuser)
def investigation_detail_manager(request, pk):
    investigation = get_object_or_404(Investigation, pk=pk)

    return render(
        request,
        "qms/investigation_detail_manager.html",
        {
            "investigation": investigation,
            "logs": investigation.logs.all(),
        }
    )


@login_required
def investigation_my_list(request):
    investigations = Investigation.objects.filter(
        staff_member=request.user
    ).order_by("-created_at")

    return render(
        request,
        "qms/investigation_my_list.html",
        {
            "investigations": investigations
        }
    )


@login_required
def investigation_staff_detail(request, pk):
    investigation = get_object_or_404(
        Investigation,
        pk=pk,
        staff_member=request.user
    )

    # Log first view (audit safe)
    if not investigation.logs.filter(event_type="notice_viewed").exists():
        InvestigationLog.objects.create(
            investigation=investigation,
            event_type="notice_viewed",
            performed_by=request.user
        )

    if request.method == "POST":
        response_text = request.POST.get("response", "").strip()

        if response_text:
            InvestigationLog.objects.create(
                investigation=investigation,
                event_type="response_submitted",
                performed_by=request.user,
                notes=response_text
            )

            investigation.status = "awaiting_response"
            investigation.save()

            messages.success(
                request,
                "Your response has been submitted."
            )

            return redirect("investigation_my_list")

    return render(
        request,
        "qms/investigation_staff_detail.html",
        {
            "investigation": investigation
        }
    )


@login_required
def investigation_add_log(request, pk):
    investigation = get_object_or_404(Investigation, pk=pk)

    if request.method == "POST":
        notes = request.POST.get("notes", "").strip()

        if notes:
            InvestigationLog.objects.create(
                investigation=investigation,
                event_type="evidence_submitted",
                performed_by=request.user,
                notes=notes,
            )
            messages.success(
                request,
                "Evidence added to investigation audit log."
            )
        else:
            messages.warning(
                request,
                "No evidence was added. Please enter notes."
            )

    return redirect(
        "investigation_detail_manager",
        pk=investigation.pk
    )
