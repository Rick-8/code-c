from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

User = settings.AUTH_USER_MODEL


class ControlledDocument(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("APPROVED", "Approved"),
        ("OBSOLETE", "Obsolete"),
    ]

    reference = models.CharField(max_length=50, unique=True)  # e.g. QMS-4.1
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)  # e.g. Context, Leadership
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # optional but useful for quick listing
    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="controlled_docs")

    def __str__(self):
        return f"{self.reference} – {self.title}"

    @property
    def current_version(self):
        return self.versions.filter(is_current=True).first()


class DocumentVersion(models.Model):
    document = models.ForeignKey(ControlledDocument, on_delete=models.CASCADE, related_name="versions")

    version_major = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    version_minor = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

    content = models.TextField()
    change_summary = models.CharField(max_length=255)

    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="doc_versions_created")
    created_at = models.DateTimeField(auto_now_add=True)

    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="doc_versions_approved")
    approved_at = models.DateTimeField(null=True, blank=True)

    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-version_major", "-version_minor"]
        unique_together = ("document", "version_major", "version_minor")

    def __str__(self):
        return f"{self.document.reference} v{self.version_major}.{self.version_minor}"

    @property
    def version_string(self):
        return f"{self.version_major}.{self.version_minor}"
