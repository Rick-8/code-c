from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.conf import settings

from .models import Product, ShopSettings, Order, OrderItem
from .forms import ProductForm
from .basket import Basket

from io import BytesIO
from PIL import Image as PILImage
from reportlab.platypus import Image

# PDF imports
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

import stripe
import os
from decimal import Decimal


# ====================================================
# ALWAYS ENSURE SHOP SETTINGS EXIST
# ====================================================
def get_settings():
    settings_obj, created = ShopSettings.objects.get_or_create(id=1)
    return settings_obj


# ====================================================
# PUBLIC — SHOP HOME
# ====================================================
def shop_home(request):
    shop = get_settings()

    if not shop.is_shop_open:
        return render(request, "shop/closed.html")

    products = Product.objects.filter(is_active=True)

    q = request.GET.get("q")
    if q:
        products = products.filter(title__icontains=q) | products.filter(description__icontains=q)

    return render(request, "shop/home.html", {
        "products": products.order_by("title"),
        "ordering_enabled": shop.ordering_enabled,
        "shop_open": shop.is_shop_open,
        "cart_count": request.session.get("cart_count", 0),
    })



# ====================================================
# PUBLIC — PRODUCT DETAIL
# ====================================================
def product_detail(request, product_id):
    shop = get_settings()

    if not shop.is_shop_open:
        return render(request, "shop/closed.html")

    product = get_object_or_404(Product, id=product_id, is_active=True)

    if product.is_staff_only and not request.user.is_staff:
        return render(request, "shop/staff_only.html", {"product": product})

    return render(request, "shop/detail.html", {
        "product": product,
        "ordering_enabled": shop.ordering_enabled,
        "shop_open": shop.is_shop_open,
    })


# ====================================================
# SUPERUSER — PRODUCT MANAGEMENT
# ====================================================
@user_passes_test(lambda u: u.is_superuser)
def manage_products(request):
    q = request.GET.get("q")
    products = Product.objects.all()

    if q:
        products = products.filter(title__icontains=q)

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


# ====================================================
# ENABLE / DISABLE SHOP (FULL CLOSURE)
# ====================================================
@user_passes_test(lambda u: u.is_superuser)
def shop_enable(request):
    shop = get_settings()
    shop.is_shop_open = True     # <-- OPEN SHOP
    shop.save()
    return redirect(request.META.get("HTTP_REFERER", "/shop/"))


@user_passes_test(lambda u: u.is_superuser)
def shop_disable(request):
    shop = get_settings()
    shop.is_shop_open = False    # <-- CLOSE SHOP
    shop.save()
    return redirect(request.META.get("HTTP_REFERER", "/shop/"))



# ====================================================
# BASKET
# ====================================================
def shop_basket(request):
    basket = Basket(request)
    return render(request, "shop/basket.html", {
        "items": basket.items(),
        "total": basket.total(),
    })


@require_POST
def basket_add(request, product_id):
    shop = get_settings()
    if not shop.ordering_enabled:
        return redirect("shop_basket")

    Basket(request).add(product_id)
    return redirect("shop_basket")


@require_POST
def basket_update(request, product_id):
    qty = int(request.POST.get("quantity", 1))
    Basket(request).update(product_id, qty)
    return redirect("shop_basket")


@require_POST
def basket_remove(request, product_id):
    Basket(request).remove(product_id)
    return redirect("shop_basket")


# ====================================================
# CHECKOUT + PAYMENT
# ====================================================
stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def checkout(request):
    basket = Basket(request)

    if basket.count() == 0:
        return redirect("shop_basket")

    user = request.user

    payroll_allowed = False
    if user.is_staff or user.is_superuser:
        payroll_allowed = all(item["product"].allow_payroll_purchase for item in basket.items())

    return render(request, "shop/checkout.html", {
        "items": basket.items(),
        "total": basket.total(),
        "payroll_allowed": payroll_allowed,
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
    })


@require_POST
def create_stripe_intent(request):
    basket = Basket(request)
    amount = int(basket.total() * 100)

    intent = stripe.PaymentIntent.create(
        amount=amount,
        currency="gbp",
        automatic_payment_methods={"enabled": True},
    )

    return JsonResponse({"clientSecret": intent.client_secret})


# ====================================================
# CONFIRM ORDER
# ====================================================
@require_POST
@login_required
def confirm_order(request):
    basket = Basket(request)
    user = request.user

    payment_method = request.POST.get("payment_method")
    payment_intent_id = request.POST.get("payment_intent")

    order = Order.objects.create(
        user=user,
        payment_method=payment_method,
        total_amount=basket.total(),
        stripe_payment_intent=payment_intent_id if payment_method == "card" else None,
        status="PAID" if payment_method == "payroll" else "PENDING",
    )

    for item in basket.items():
        OrderItem.objects.create(
            order=order,
            product=item["product"],
            quantity=item["quantity"],
            line_total=item["line_total"],
        )

    basket.clear()

    return render(request, "shop/order_complete.html", {"order": order})


# ====================================================
# STRIPE WEBHOOK
# ====================================================
@csrf_exempt
def stripe_webhook(request):
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception:
        return HttpResponse(status=400)

    if event["type"] == "payment_intent.succeeded":
        pi = event["data"]["object"]["id"]

        try:
            order = Order.objects.get(stripe_payment_intent=pi)
            order.status = "PAID"
            order.save()
        except Order.DoesNotExist:
            pass

    return HttpResponse(status=200)


# ====================================================
# CUSTOMER ORDER PAGES
# ====================================================
@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "shop/orders.html", {"orders": orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "shop/order_detail.html", {"order": order})


# ====================================================
# STAFF — MANAGE ORDERS
# ====================================================
@staff_member_required
def manage_orders(request):
    q = request.GET.get("q")
    status_filter = request.GET.get("status")

    orders = Order.objects.all().order_by("-created_at")

    if q:
        orders = orders.filter(user__username__icontains=q)

    if status_filter:
        orders = orders.filter(status=status_filter)

    return render(request, "shop/manage_orders.html", {"orders": orders})


@staff_member_required
def manage_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "shop/manage_order_detail.html", {"order": order})


@staff_member_required
def order_mark_dispatched(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = "DISPATCHED"
    order.save()
    return redirect("manage_order_detail", order_id=order_id)


@staff_member_required
def order_mark_collected(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = "COLLECTED"
    order.save()
    return redirect("manage_order_detail", order_id=order_id)


# ====================================================
# PAYROLL PDF (PLATYPUS VERSION)
# ====================================================
@login_required
def payroll_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Restrict to payroll orders only
    if order.payment_method != "payroll":
        return HttpResponse("This order was not paid via payroll deduction.", status=403)

    # PDF response
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f"attachment; filename=payroll_deduction_order_{order.id}.pdf"
    )

    # PDF document
    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=50,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    story = []

    # =============================
    #  LOGO (WebP → PNG conversion)
    # =============================
    logo_path = os.path.join(settings.BASE_DIR, "static/css/media/LOGO-Cozys.webp")

    try:
        pil_logo = PILImage.open(logo_path).convert("RGB")

        # Resize while keeping aspect ratio
        max_width = 140
        w_percent = max_width / float(pil_logo.size[0])
        new_height = int(float(pil_logo.size[1]) * float(w_percent))

        pil_logo = pil_logo.resize((max_width, new_height))

        # Convert into bytes so ReportLab can read it as PNG
        logo_buffer = BytesIO()
        pil_logo.save(logo_buffer, format="PNG")
        logo_buffer.seek(0)

        logo = Image(logo_buffer)
        logo.hAlign = "RIGHT"

        story.append(logo)
        story.append(Spacer(1, 16))

    except Exception as e:
        story.append(Paragraph("<b>Cozy Coaches</b>", styles["Heading1"]))
        story.append(Spacer(1, 12))

    # =============================
    #     HEADER
    # =============================
    title = Paragraph(
        "<b>Payroll Deduction Form</b>",
        ParagraphStyle(
            "title",
            parent=styles["Heading1"],
            fontSize=20,
            textColor=colors.darkblue,
            spaceAfter=20,
        ),
    )
    story.append(title)

    # =============================
    #   ORDER DETAILS
    # =============================
    info = styles["Normal"]
    story.append(Paragraph(f"<b>Employee:</b> {order.user.get_full_name()} ({order.user.username})", info))
    story.append(Paragraph(f"<b>Order ID:</b> {order.id}", info))
    story.append(Paragraph(f"<b>Date:</b> {order.created_at.strftime('%d %b %Y %H:%M')}", info))
    story.append(Spacer(1, 16))

    # =============================
    #  ITEMS TABLE
    # =============================
    data = [["Item", "Qty", "Line Total (£)"]]

    for item in order.items.all():
        data.append([
            item.product.title,
            str(item.quantity),
            f"{item.line_total}"
        ])

    table = Table(
        data,
        colWidths=[260, 50, 80]
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
    ]))

    story.append(table)
    story.append(Spacer(1, 20))

    # =============================
    #   TOTAL
    # =============================
    story.append(
        Paragraph(
            f"<b>Total Amount: £{order.total_amount}</b>",
            ParagraphStyle(
                "total",
                parent=styles["Heading2"],
                textColor=colors.darkred,
                spaceAfter=25,
            ),
        )
    )

    # =============================
    #   DECLARATION
    # =============================
    declaration = (
        "I authorise Cozy Coaches Payroll Department to deduct the above total amount "
        "from my next salary payment as part of the company shop purchase scheme."
        "<br/><br/><b>Signed:</b> ________________________________"
        "<br/><br/><b>Date:</b> __________________________________"
    )

    story.append(Paragraph(declaration, styles["Normal"]))

    # Build PDF
    doc.build(story)

    return response


# ====================================================
# STAFF — MARK PAYROLL AS COMPLETED
# ====================================================
@staff_member_required
def order_mark_payroll_complete(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.payment_method != "payroll":
        messages.error(request, "This is not a payroll order.")
        return redirect("manage_order_detail", order_id=order.id)

    order.status = "COMPLETED"
    order.save()

    messages.success(request, "Payroll deduction marked as completed.")
    return redirect("manage_order_detail", order_id=order.id)