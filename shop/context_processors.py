def shop_settings(request):
    ordering = request.session.get("ordering_enabled", True)
    return {
        "ordering_enabled": ordering
    }
