from .models import LiveOpsCredential


def user_can_manage_ops(user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return LiveOpsCredential.objects.filter(user=user, is_enabled=True).exists()
