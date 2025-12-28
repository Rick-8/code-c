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
from django.contrib.auth import authenticate
from .forms import AppointPrimaryAuthorityForm
from .models import QMSAuthority, QMSChangeLog
from .models import Responsibility


from django.db.models import Q

from .permissions import is_primary_qms_authority

from .models import Interaction, InteractionAssignmentLog
from .forms import InteractionForm

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives


User = get_user_model()


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
# UPDATE INTERACTION (ASSIGN / REASSIGN / LOG / CLOSE)
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
        previous_status = interaction.status

        new_assignee = None
        if new_assigned_to_id:
            new_assignee = get_object_or_404(User, pk=new_assigned_to_id)

        email_required = False

        # ─────────────────────────────
        # GUARD RAILS (ISO CONTROL)
        # ─────────────────────────────
        if interaction.status == "closed" and previous_assignee != new_assignee:
            messages.error(request, "Closed interactions cannot be reassigned.")
            return redirect("qms_manager_list")

        if new_status == "closed" and not manager_notes:
            messages.error(
                request,
                "Manager notes are required before closing an interaction."
            )
            return redirect("qms_manager_list")

        # ─────────────────────────────
        # ASSIGNMENT / REASSIGNMENT LOG
        # ─────────────────────────────
        if previous_assignee != new_assignee:
            InteractionAssignmentLog.objects.create(
                interaction=interaction,
                previous_assignee=previous_assignee,
                new_assignee=new_assignee,
                changed_by=request.user,
                reason=(
                    reassignment_reason
                    if previous_assignee
                    else "Initial assignment"
                ),
            )
            interaction.assigned_to = new_assignee
            email_required = True

        # ─────────────────────────────
        # MANAGER NOTES → AUDIT LOG
        # ─────────────────────────────
        if manager_notes:
            InteractionAssignmentLog.objects.create(
                interaction=interaction,
                previous_assignee=interaction.assigned_to,
                new_assignee=interaction.assigned_to,
                changed_by=request.user,
                reason=manager_notes,
            )
            interaction.manager_notes = ""
            email_required = True

        # ─────────────────────────────
        # STATUS CHANGE LOG
        # ─────────────────────────────
        if previous_status != new_status:
            InteractionAssignmentLog.objects.create(
                interaction=interaction,
                previous_assignee=interaction.assigned_to,
                new_assignee=interaction.assigned_to,
                changed_by=request.user,
                reason=(
                    f"Status changed from "
                    f"{interaction.get_status_display()} "
                    f"to {dict(Interaction.STATUS_CHOICES).get(new_status)}"
                ),
            )
            email_required = True

        # ─────────────────────────────
        # FINAL SAVE
        # ─────────────────────────────
        interaction.status = new_status

        if new_status == "closed" and interaction.closed_at is None:
            interaction.closed_at = timezone.now()

        interaction.save()

        # ─────────────────────────────
        # EMAIL NOTIFICATION (TEMPLATE)
        # ─────────────────────────────
        if email_required and interaction.assigned_to and interaction.assigned_to.email:

            context = {
                "interaction": interaction,
                "interaction_type": interaction.get_interaction_type_display(),
                "service": interaction.get_service_line_display(),
                "severity": interaction.get_severity_display(),
                "status": interaction.get_status_display(),
                "assigned_by": request.user.get_full_name() or request.user.username,
                "site_url": request.build_absolute_uri("/"),
            }

            subject = "QMS Interaction Update"

            text_body = render_to_string(
                "qms/emails/interaction_assigned.txt",
                context
            )

            html_body = render_to_string(
                "qms/emails/interaction_assigned.html",
                context
            )

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[interaction.assigned_to.email],
            )

            email.attach_alternative(html_body, "text/html")
            email.send(fail_silently=True)

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


@login_required
def confirm_primary_authority(request):
    if request.method == "POST":
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=request.user.username,
            password=password,
        )

        if user is None:
            messages.error(request, "Password confirmation failed.")
            return redirect("qms_confirm_primary")

        # ✅ SINGLE SOURCE OF TRUTH
        request.session["primary_qms_confirmed"] = True
        request.session.set_expiry(0)  # expires on browser close

        messages.success(
            request,
            "Primary QMS Authority confirmed for this session."
        )

        return redirect("qms_dashboard")

    return render(request, "qms/confirm_primary.html")


@login_required
def primary_authority_list(request):
    if not request.session.get("qms_primary_confirmed"):
        return redirect("qms_confirm_primary")

    authorities = QMSAuthority.objects.select_related("user").order_by(
        "-is_primary",
        "-created_at"
    )

    return render(
        request,
        "qms/primary_authority_list.html",
        {"authorities": authorities}
    )


@login_required
def revoke_primary_authority(request, authority_id):
    """
    Revoke a Primary QMS Authority.
    Non-destructive, fully logged, reversible.
    """

    authority = get_object_or_404(
        QMSAuthority,
        pk=authority_id,
        revoked_at__isnull=True,
    )

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()

        # Revoke using model method (single source of truth)
        authority.revoke(
            by_user=request.user,
            reason=reason,
        )

        # Permanent audit log
        QMSChangeLog.objects.create(
            page="PRIMARY_AUTHORITY",
            object_ref=authority.user.get_username(),
            action="Primary authority revoked",
            description=reason,
            performed_by=request.user,
        )

        messages.success(
            request,
            f"{authority.user.get_full_name() or authority.user.username} "
            "has been revoked as a Primary QMS Authority."
        )

        return redirect("qms_primary_list")

    return render(
        request,
        "qms/revoke_primary_confirm.html",
        {
            "authority": authority,
        },
    )



@login_required
def qms_dashboard(request):
    return render(request, "qms/dashboard.html")


@login_required
def qms_primary_list(request):
    """
    View the Primary QMS Authority register.
    Requires primary authority to be confirmed.
    """

    if not request.session.get("primary_qms_confirmed"):
        messages.error(request, "Primary QMS Authority confirmation required.")
        return redirect("qms_confirm_primary")

    authorities = QMSAuthority.objects.select_related(
        "user", "appointed_by"
    ).order_by("-appointed_at")

    return render(
        request,
        "qms/primary_authority_list.html",
        {"authorities": authorities},
    )


@login_required
def responsibility_register_readonly(request):
    """
    Read-only Depot / Responsibility Register.
    Used for document tiles, audits, and general visibility.
    No editing permitted.
    """

    responsibilities = Responsibility.objects.select_related(
        "responsible_person",
        "assigned_by",
    ).order_by("-effective_from")

    return render(
        request,
        "qms/responsibility_register_readonly.html",
        {
            "responsibilities": responsibilities,
        },
    )


@login_required
def responsibility_register(request):
    """
    Depot / Responsibility Register
    Primary QMS Authority protected
    """

    if not request.session.get("primary_qms_confirmed"):
        messages.error(request, "Primary QMS Authority confirmation required.")
        return redirect("qms_confirm_primary")

    responsibilities = Responsibility.objects.select_related(
        "responsible_person",
        "assigned_by",
    ).order_by("-effective_from")

    # ✅ STAFF + SUPERUSER (this fixes your empty list)
    staff_users = User.objects.filter(
        Q(is_staff=True) | Q(is_superuser=True),
        is_active=True,
    ).order_by("first_name", "last_name")

    if request.method == "POST":
        Responsibility.objects.create(
            depot=request.POST.get("depot"),
            area=request.POST.get("area", ""),
            role=request.POST.get("role"),
            responsible_person_id=request.POST.get("responsible_person"),
            assigned_by=request.user,
            effective_from=request.POST.get("effective_from"),
            is_active=True,
        )

        messages.success(
            request,
            "Responsibility added and recorded in the governance register."
        )

        # ISO-safe redirect (prevents double submit)
        return redirect("responsibility_register")

    return render(
        request,
        "qms/responsibility_register.html",
        {
            "responsibilities": responsibilities,
            "staff_users": staff_users,
        },
    )



@login_required
def appoint_primary_authority(request):
    if not request.session.get("primary_qms_confirmed"):
        messages.error(request, "Primary QMS Authority confirmation required.")
        return redirect("qms_confirm_primary")

    form = AppointPrimaryAuthorityForm()

    if request.method == "POST":
        form = AppointPrimaryAuthorityForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]

           # Either revive existing authority OR create new
            authority, created = QMSAuthority.objects.get_or_create(
                user=user,
                defaults={
                    "is_primary": True,
                    "appointed_by": request.user,
                },
            )

            if not created:
                # Revived authority (audit-safe)
                authority.is_primary = True
                authority.revoked_at = None
                authority.revoked_by = None
                authority.reason = ""
                authority.appointed_by = request.user
                authority.appointed_at = timezone.now()
                authority.save()


            # Log action
            QMSChangeLog.objects.create(
                page="PRIMARY_AUTHORITY",
                object_ref=user.get_username(),
                action="Primary QMS authority appointed",
                description="Appointed via QMS Authority Register",
                performed_by=request.user,
            )

            messages.success(
                request,
                f"{user.get_full_name() or user.username} appointed as Primary QMS Authority."
            )

            return redirect("qms_primary_list")

    return render(
        request,
        "qms/appoint_primary_authority.html",
        {"form": form}
    )
