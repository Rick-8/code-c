from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


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

    # ── Classification ─────────────────────────────────────
    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPE_CHOICES
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES
    )
    service_line = models.CharField(
        max_length=20,
        choices=SERVICE_LINE_CHOICES
    )

    # ── Timing ─────────────────────────────────────────────
    occurred_at = models.DateTimeField(
        help_text="When the issue occurred"
    )
    logged_at = models.DateTimeField(
        auto_now_add=True
    )
    closed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # ── Content ────────────────────────────────────────────
    summary = models.TextField()
    severity = models.PositiveSmallIntegerField(
        choices=SEVERITY_CHOICES,
        default=1
    )

    # ── Traceability ───────────────────────────────────────
    driver_name = models.CharField(
        max_length=255,
        blank=True
    )
    vehicle_reference = models.CharField(
        max_length=50,
        blank=True
    )
    route_reference = models.CharField(
        max_length=100,
        blank=True
    )

    # ── Management ─────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open'
    )
    manager_notes = models.TextField(
        blank=True
    )

    # ── Assignment ─────────────────────────────────────────
    assigned_to = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_qms_interactions'
    )

    # ── Ownership ──────────────────────────────────────────
    logged_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='qms_interactions'
    )

    def __str__(self):
        return f"{self.get_interaction_type_display()} | {self.get_status_display()}"


# ──────────────────────────────────────────────────────────
# Assignment / Reassignment Audit Log (ISO 9001 Evidence)
# ──────────────────────────────────────────────────────────

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

    changed_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return (
            f"Assignment change on Interaction {self.interaction.id} "
            f"at {self.changed_at:%d %b %Y %H:%M}"
        )
