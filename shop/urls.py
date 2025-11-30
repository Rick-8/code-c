from django.urls import path
from . import views

urlpatterns = [
    # Public shop
    path("", views.shop_home, name="shop_home"),
    path("product/<int:product_id>/", views.product_detail, name="shop_product_detail"),

    # Basket
    path("basket/", views.shop_basket, name="shop_basket"),
    path("basket/add/<int:product_id>/", views.basket_add, name="basket_add"),
    path("basket/update/<int:product_id>/", views.basket_update, name="basket_update"),
    path("basket/remove/<int:product_id>/", views.basket_remove, name="basket_remove"),

    # Checkout
    path("checkout/", views.checkout, name="shop_checkout"),
    path("checkout/create-intent/", views.create_stripe_intent, name="shop_create_intent"),
    path("checkout/confirm/", views.confirm_order, name="confirm_order"),

    # Webhook
    path("webhook/", views.stripe_webhook, name="shop_webhook"),

    # Customer orders
    path("my-orders/", views.my_orders, name="my_orders"),
    path("my-orders/<int:order_id>/", views.order_detail, name="order_detail"),

    # Staff management
    path("manage/", views.manage_products, name="shop_manage_products"),
    path("manage/add/", views.add_product, name="shop_add_product"),
    path("manage/edit/<int:product_id>/", views.edit_product, name="shop_edit_product"),
    path("manage/delete/<int:product_id>/", views.delete_product, name="shop_delete_product"),

    # Staff order management
    path("manage/orders/", views.manage_orders, name="manage_orders"),
    path("manage/orders/<int:order_id>/", views.manage_order_detail, name="manage_order_detail"),
    path("manage/orders/<int:order_id>/dispatch/", views.order_mark_dispatched, name="order_mark_dispatched"),
    path("manage/orders/<int:order_id>/collect/", views.order_mark_collected, name="order_mark_collected"),
    path("orders/<int:order_id>/payroll-pdf/", views.payroll_pdf, name="payroll_pdf"),
    path("manage/orders/<int:order_id>/payroll-complete/",
        views.order_mark_payroll_complete,
        name="order_mark_payroll_complete"),




    # Enable/disable shop
    path("enable/", views.shop_enable, name="shop_enable"),
    path("disable/", views.shop_disable, name="shop_disable"),
]
