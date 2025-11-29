from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from .models import Product, ShopSettings
from django.conf import settings


# ====================================================
# Helper to ensure settings always exist
# ====================================================
def get_settings():
    settings, created = ShopSettings.objects.get_or_create(id=1)
    return settings


# ====================================================
# SHOP HOME (public)
# ====================================================
def shop_home(request):
    settings = get_settings()

    if not settings.is_shop_open:
        return render(request, "shop/closed.html")

    products = Product.objects.filter(is_active=True)

    # Search filter
    q = request.GET.get("q")
    if q:
        products = products.filter(
            title__icontains=q
        ) | products.filter(
            description__icontains=q
        )

    return render(request, "shop/home.html", {
        "products": products.order_by("title"),
        "ordering_enabled": settings.ordering_enabled,
        "cart_count": request.session.get("cart_count", 0),  # future
    })



# ====================================================
# PRODUCT DETAIL (public)
# ====================================================
def product_detail(request, product_id):
    settings = get_settings()

    # Shop closed completely
    if not settings.is_shop_open:
        return render(request, "shop/closed.html")

    product = get_object_or_404(Product, id=product_id, is_active=True)

    # Staff-only restrictions
    if product.is_staff_only and not request.user.is_staff:
        return render(request, "shop/staff_only.html", {
            "product": product
        })

    return render(request, "shop/detail.html", {
        "product": product,
        "ordering_enabled": settings.ordering_enabled,
    })


# ====================================================
# SHOP SETTINGS PAGE (superuser only)
# ====================================================
@user_passes_test(lambda u: u.is_superuser)
def shop_settings_page(request):
    settings = get_settings()

    if request.method == "POST":
        # Toggle shop visibility
        if "toggle_shop" in request.POST:
            settings.is_shop_open = not settings.is_shop_open

        # Toggle ordering availability
        if "toggle_ordering" in request.POST:
            settings.ordering_enabled = not settings.ordering_enabled

        settings.save()
        return redirect("shop_settings")

    return render(request, "shop/settings.html", {
        "settings": settings,
    })

from django.contrib import messages
from .forms import ProductForm

# ============================
# SUPERUSER PRODUCT MANAGEMENT
# ============================

@user_passes_test(lambda u: u.is_superuser)
def manage_products(request):
    products = Product.objects.all().order_by("-id")
    return render(request, "shop/manage_products.html", {"products": products})


@user_passes_test(lambda u: u.is_superuser)
def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Product added successfully.")
            return redirect("shop_manage_products")
    else:
        form = ProductForm()

    return render(request, "shop/add_product.html", {"form": form})


@user_passes_test(lambda u: u.is_superuser)
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Product updated.")
        return redirect("shop_manage_products")

    return render(request, "shop/edit_product.html", {"form": form, "product": product})


@user_passes_test(lambda u: u.is_superuser)
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, "Product deleted.")
    return redirect("shop_manage_products")


def shop_basket(request):
    """
    Temporary placeholder basket page.
    Prevents URL errors until the basket system is built.
    """
    return render(request, "shop/basket.html")


def shop_orders(request):
    """
    Temporary placeholder orders page.
    """
    return render(request, "shop/orders.html")


# Helper: Only superusers can toggle shop
superuser_required = user_passes_test(lambda u: u.is_superuser)

@superuser_required
def shop_enable(request):
    settings.ORDERING_ENABLED = True
    request.session['ordering_enabled'] = True
    return redirect(request.META.get("HTTP_REFERER", "/shop/"))

@superuser_required
def shop_disable(request):
    settings.ORDERING_ENABLED = False
    request.session['ordering_enabled'] = False
    return redirect(request.META.get("HTTP_REFERER", "/shop/"))