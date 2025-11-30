from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from .models import Product, ShopSettings
from django.conf import settings
from django.views.decorators.http import require_POST
from .basket import Basket
from django.http import JsonResponse
from .models import Order, OrderItem
from decimal import Decimal
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required



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


@require_POST
def basket_add(request, product_id):
    settings_obj = get_settings()
    if not settings_obj.ordering_enabled:
        return redirect("shop_basket")

    basket = Basket(request)
    basket.add(product_id)
    return redirect("shop_basket")


@require_POST
def basket_update(request, product_id):
    qty = int(request.POST.get("quantity", 1))
    basket = Basket(request)
    basket.update(product_id, qty)
    return redirect("shop_basket")


@require_POST
def basket_remove(request, product_id):
    basket = Basket(request)
    basket.remove(product_id)
    return redirect("shop_basket")


stripe.api_key = settings.STRIPE_SECRET_KEY


def checkout(request):
    basket = Basket(request)

    if basket.count() == 0:
        return redirect("shop_basket")

    # Payroll allowed only if user is staff & product allows payroll
    payroll_allowed = False
    if request.user.is_staff or request.user.is_superuser:
        payroll_allowed = all(
            item["product"].allow_payroll_purchase
            for item in basket.items()
        )

    return render(request, "shop/checkout.html", {
        "items": basket.items(),
        "total": basket.total(),
        "payroll_allowed": payroll_allowed,
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
    })


@require_POST
def create_stripe_intent(request):
    basket = Basket(request)
    amount = int(basket.total() * 100)  # in pence

    intent = stripe.PaymentIntent.create(
        amount=amount,
        currency="gbp",
        automatic_payment_methods={"enabled": True},
    )

    return JsonResponse({"clientSecret": intent.client_secret})


@require_POST
def confirm_order(request):
    basket = Basket(request)

    payment_method = request.POST.get("payment_method")
    payment_intent_id = request.POST.get("payment_intent")

    order = Order.objects.create(
        user=request.user,
        payment_method=payment_method,
        total_amount=basket.total(),
        stripe_payment_intent=payment_intent_id
    )

    for item in basket.items():
        OrderItem.objects.create(
            order=order,
            product=item["product"],
            quantity=item["quantity"],
            line_total=item["line_total"]
        )

    basket.clear()

    return render(request, "shop/order_complete.html", {"order": order})


def shop_basket(request):
    basket = Basket(request)

    return render(request, "shop/basket.html", {
        "items": basket.items(),
        "total": basket.total(),
    })


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # Payment succeeded
    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        pi_id = intent["id"]

        try:
            order = Order.objects.get(stripe_payment_intent=pi_id)
            order.status = "PAID"
            order.save()
        except Order.DoesNotExist:
            pass

    return HttpResponse(status=200)


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "shop/orders.html", {"orders": orders})


@login_required
def order_detail(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, "shop/order_detail.html", {"order": order})


@staff_member_required
def manage_orders(request):
    orders = Order.objects.all().order_by("-created_at")
    return render(request, "shop/manage_orders.html", {"orders": orders})


@staff_member_required
def manage_order_detail(request, order_id):
    order = Order.objects.get(id=order_id)
    return render(request, "shop/manage_order_detail.html", {"order": order})


@staff_member_required
def order_mark_dispatched(request, order_id):
    order = Order.objects.get(id=order_id)
    order.status = "DISPATCHED"
    order.save()
    return redirect("manage_order_detail", order_id=order.id)


@staff_member_required
def order_mark_collected(request, order_id):
    order = Order.objects.get(id=order_id)
    order.status = "COLLECTED"
    order.save()
    return redirect("manage_order_detail", order_id=order.id)
