from .models import QMSAuthority


def is_primary_qms_authority(user):
    if not user or not user.is_authenticated:
        return False

    return QMSAuthority.objects.filter(
        user=user,
        is_primary=True,
        revoked_at__isnull=True
    ).exists()
