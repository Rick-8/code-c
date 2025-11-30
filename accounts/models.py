from django.db import models
from django.contrib.auth.models import User


def cv_upload_path(instance, filename):
    return f"cv_uploads/user_{instance.user.id}/{filename}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    phone = models.CharField(max_length=20, blank=True)
    address_1 = models.CharField(max_length=255, blank=True)
    address_2 = models.CharField(max_length=255, blank=True)
    town = models.CharField(max_length=100, blank=True)
    postcode = models.CharField(max_length=20, blank=True)

    cv = models.FileField(upload_to=cv_upload_path, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Profile"
