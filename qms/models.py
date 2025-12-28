from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import random
from django.db import IntegrityError
from django.conf import settings
from django.core.exceptions import ValidationError

User = get_user_model()


# =========================================================
# QMS INTERACTIONS
# =========================================================

class Interaction(models.Model):

    INTERACTION_TYPE_CHOICES = [
        ('complaint', 'Complaint'),
        ('incident', 'Incident / Accident'),
        ('praise', 'Praise'),
        ('defect', 'Vehicle Defect'),
        ('feedback', 'General Feedback'),
        ('other', 'Other'),
    ]

    SOURCE_CHOICES = [
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('social', 'Social Media'),
        ('in_person', 'In Person'),
        ('flixbus', 'FlixBus System'),
        ('internal', 'Internal / Staff'),
    ]

    SERVICE_LINE_CHOICES = [
        ('flixbus', 'FlixBus'),
        ('school', 'Home to School'),
        ('private', 'Private Hire'),
        ('other', 'Other'),
    ]

    SEVERITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ]

    # ── Classification ────────────────────────────────────
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPE_CHOICES)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    service_line = models.CharField(max_length=20, choices=SERVICE_LINE_CHOICES)

    # ── Timing ────────────────────────────────────────────
    occurred_at = models.DateTimeField(help_text="When the issue occurred")
    logged_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # ── Content ───────────────────────────────────────────
    summary = models.TextField()
    severity = models.PositiveSmallIntegerField(choices=SEVERITY_CHOICES, default=1)

    # ── Traceability ──────────────────────────────────────
    driver_name = models.CharField(max_length=255, blank=True)
    vehicle_reference = models.CharField(max_length=50, blank=True)
    route_reference = models.CharField(max_length=100, blank=True)

    # ── Management ────────────────────────────────────────
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    manager_notes = models.TextField(blank=True)

    # ── Assignment ────────────────────────────────────────
    assigned_to = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_qms_interactions'
    )

    # ── Ownership ─────────────────────────────────────────
    logged_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='qms_interactions'
    )

    def __str__(self):
        return f"{self.get_interaction_type_display()} | {self.get_status_display()}"


# =========================================================
# INTERACTION ASSIGNMENT AUDIT LOG (ISO 9001)
# =========================================================

class InteractionAssignmentLog(models.Model):

    interaction = models.ForeignKey(
        Interaction,
        on_delete=models.CASCADE,
        related_name="assignment_logs"
    )

    previous_assignee = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+"
    )

    new_assignee = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+"
    )

    changed_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+"
    )

    reason = models.TextField(
        blank=True,
        help_text="Required when an interaction is reassigned"
    )

    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return (
            f"Assignment change on Interaction {self.interaction.id} "
            f"at {self.changed_at:%d %b %Y %H:%M}"
        )


# =========================================================
# FORMAL STAFF INVESTIGATIONS
# =========================================================

class Investigation(models.Model):

    STATUS_CHOICES = [
        ("open", "Open"),
        ("awaiting_response", "Awaiting Staff Response"),
        ("no_further_action", "No Further Action"),
        ("training", "Training Required"),
        ("disciplinary", "Escalated to Disciplinary"),
        ("closed", "Closed"),
    ]

    case_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text="Unique investigation reference number"
    )

    staff_member = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="investigations"
    )

    reason = models.TextField(
        help_text="Reason for investigation"
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="open"
    )

    created_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_investigations"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # ─────────────────────────────────────────────
    # AUTO CASE NUMBER GENERATION (ROBUST)
    # Format: CTI-YY-XXXXXX
    # ─────────────────────────────────────────────
    def save(self, *args, **kwargs):
        if not self.case_number:
            year_suffix = timezone.now().strftime("%y")

            for _ in range(10):  # hard stop safety
                random_part = random.randint(100000, 999999)
                candidate = f"CTI-{year_suffix}-{random_part}"

                if not Investigation.objects.filter(case_number=candidate).exists():
                    self.case_number = candidate
                    break
            else:
                # This should realistically never happen
                raise ValueError("Unable to generate unique Investigation case number")

        super().save(*args, **kwargs)

    def __str__(self):
        return self.case_number

# =========================================================
# INVESTIGATION AUDIT LOG (ISO 9001 / HR SAFE)
# =========================================================


class InvestigationLog(models.Model):

    EVENT_CHOICES = [
        ("created", "Investigation Created"),
        ("notice_sent", "Investigation Notice Sent"),
        ("notice_viewed", "Employee Viewed Notice"),
        ("response_submitted", "Employee Response Submitted"),
        ("evidence_submitted", "Evidence Submitted"),
        ("decision_made", "Manager Decision Recorded"),
        ("closed", "Investigation Closed"),
        ("escalated", "Escalated to Disciplinary"),
    ]

    investigation = models.ForeignKey(
        Investigation,
        on_delete=models.CASCADE,
        related_name="logs"
    )

    event_type = models.CharField(
        max_length=30,
        choices=EVENT_CHOICES
    )

    performed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.get_event_type_display()} – {self.created_at:%d %b %Y %H:%M}"


class QMSAuthority(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="qms_authority"
    )

    is_primary = models.BooleanField(default=False)

    appointed_at = models.DateTimeField(auto_now_add=True)
    appointed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointed_qms_authorities"
    )

    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revoked_qms_authorities"
    )

    reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "QMS Authority"
        verbose_name_plural = "QMS Authorities"

    def clean(self):
        if self.is_primary:
            qs = QMSAuthority.objects.filter(
                is_primary=True,
                revoked_at__isnull=True
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.count() >= 2:
                raise ValidationError(
                    "Only two Primary QMS Authorities may exist."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def revoke(self, by_user, reason=""):
        """
        Safely revoke this authority (audit-safe, non-destructive).
        """
        if self.revoked_at:
            return  # already revoked, do nothing

        self.revoked_at = timezone.now()
        self.revoked_by = by_user
        self.reason = reason
        self.is_primary = False
        self.save(update_fields=[
            "revoked_at",
            "revoked_by",
            "reason",
            "is_primary",
        ])

    def __str__(self):
        return f"{self.user} – {'Primary' if self.is_primary else 'Standard'}"


class QMSChangeLog(models.Model):
    PAGE_CHOICES = [
        ("PRIMARY_AUTHORITY", "Primary QMS Authority Register"),
        ("DEPOT_RESPONSIBILITY", "Depot Responsibility Register"),
        ("STAFF_RESPONSIBILITY", "Staff Responsibility Register"),
    ]

    page = models.CharField(max_length=50, choices=PAGE_CHOICES)

    # Human-friendly reference to what changed (username, depot name, record ID, etc.)
    object_ref = models.CharField(max_length=255)

    # Short label for the event: "Authority revoked", "Responsibility assigned", etc.
    action = models.CharField(max_length=120)

    # Optional details (reason/notes)
    description = models.TextField(blank=True)

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="qms_change_logs",
    )

    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-performed_at"]

    def __str__(self):
        return f"{self.page} | {self.action} | {self.object_ref}"
