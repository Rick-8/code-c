from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# =========================================================
# LIVE OPS CREDENTIALS
# =========================================================

class LiveOpsCredential(models.Model):
    """
    Tick access for staff users who are allowed into Live Ops.
    Superusers automatically allowed (checked in permission helper).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="live_ops_credential",
    )
    is_enabled = models.BooleanField(default=False)
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="granted_live_ops_credentials",
    )

    def __str__(self):
        return f"LiveOpsCredential({self.user})"


# =========================================================
# LIVE OPS ROUTES + JOURNEYS
# =========================================================

class OpsRoute(models.Model):
    """
    Management-defined route definition (CRUD).
    """
    code = models.CharField(max_length=20, unique=True)  # e.g. J81, FLIX-123
    name = models.CharField(max_length=120)             # e.g. "Bedford → London"
    origin = models.CharField(max_length=120)
    destination = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class OpsJourney(models.Model):
    """
    A dated 'run' of a route that carries the live status.
    """
    STATUS_ON_TIME = "on_time"
    STATUS_DELAYED = "delayed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_ON_TIME, "On time"),
        (STATUS_DELAYED, "Delayed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    route = models.ForeignKey(OpsRoute, on_delete=models.CASCADE, related_name="journeys")

    service_date = models.DateField(default=timezone.localdate)
    planned_departure = models.TimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ON_TIME)

    # Required when DELAYED
    delay_minutes = models.PositiveIntegerField(null=True, blank=True)

    # Required when DELAYED or CANCELLED
    reason = models.TextField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ops_updates",
    )

    class Meta:
        ordering = ["-service_date", "route__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["route", "service_date", "planned_departure"],
                name="uniq_ops_route_date_departure",
            )
        ]

    def clean(self):
        if self.status == self.STATUS_DELAYED:
            if self.delay_minutes is None:
                raise ValidationError({"delay_minutes": "Delay minutes are required when status is Delayed."})
            if not self.reason.strip():
                raise ValidationError({"reason": "A reason is required when status is Delayed."})

        if self.status == self.STATUS_CANCELLED:
            if not self.reason.strip():
                raise ValidationError({"reason": "A reason is required when status is Cancelled."})
            if self.delay_minutes is not None:
                raise ValidationError({"delay_minutes": "Delay minutes must be empty when status is Cancelled."})

        if self.status == self.STATUS_ON_TIME:
            self.delay_minutes = None
            self.reason = ""

    @property
    def badge_class(self) -> str:
        if self.status == self.STATUS_ON_TIME:
            return "bg-success"
        if self.status == self.STATUS_DELAYED:
            return "bg-warning text-dark"
        return "bg-danger"

    def __str__(self):
        return f"{self.route.code} {self.service_date} ({self.status})"


# home/models.py (add this model)

class OpsChangeLog(models.Model):
    ACTION_ROUTE_CREATED = "route_created"
    ACTION_ROUTE_DISCONTINUED = "route_discontinued"
    ACTION_JOURNEY_UPDATED = "journey_updated"

    ACTION_CHOICES = [
        (ACTION_ROUTE_CREATED, "Route created"),
        (ACTION_ROUTE_DISCONTINUED, "Route discontinued"),
        (ACTION_JOURNEY_UPDATED, "Journey updated"),
    ]

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)

    route = models.ForeignKey(
        "OpsRoute",
        on_delete=models.CASCADE,
        related_name="change_logs",
    )
    journey = models.ForeignKey(
        "OpsJourney",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_logs",
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ops_changes",
    )

    note = models.CharField(max_length=255, blank=True)

    old_status = models.CharField(max_length=20, blank=True, default="")
    new_status = models.CharField(max_length=20, blank=True, default="")

    old_delay_minutes = models.IntegerField(null=True, blank=True)
    new_delay_minutes = models.IntegerField(null=True, blank=True)

    old_reason = models.TextField(blank=True, default="")
    new_reason = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_action_display()} - {self.route.code} @ {self.created_at:%Y-%m-%d %H:%M}"


class OpsDailyJournal(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ops_daily_journals",
    )
    entry_date = models.DateField(db_index=True)
    content = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "entry_date")
        ordering = ["-entry_date", "-updated_at"]

    def __str__(self):
        return f"{self.user} — {self.entry_date}"


class OpsDailyJournalRevision(models.Model):
    journal = models.ForeignKey(
        OpsDailyJournal,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    saved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ops_journal_revisions",
    )
    saved_at = models.DateTimeField(auto_now_add=True)
    content_snapshot = models.TextField()

    class Meta:
        ordering = ["-saved_at"]

    def __str__(self):
        return f"{self.journal.user} — {self.journal.entry_date} @ {self.saved_at:%H:%M}"


class OpsTodoItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ops_todos",
    )

    title = models.CharField(max_length=200)
    is_done = models.BooleanField(default=False)
    done_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["is_done", "-created_at"]

    def __str__(self):
        state = "done" if self.is_done else "open"
        return f"{self.title} ({state})"
