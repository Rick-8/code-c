from .models import ShopSettings


def shop_settings(request):
    settings_obj, created = ShopSettings.objects.get_or_create(id=1)
    return {
        "ordering_enabled": settings_obj.ordering_enabled,
        "shop_open": settings_obj.is_shop_open,
    }
