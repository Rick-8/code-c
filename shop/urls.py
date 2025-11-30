from django.urls import path
from . import views

urlpatterns = [
    path("", views.shop_home, name="shop_home"),
    path("product/<int:product_id>/", views.product_detail, name="shop_product_detail"),
    path("basket/add/<int:product_id>/", views.basket_add, name="basket_add"),
    path("basket/update/<int:product_id>/", views.basket_update, name="basket_update"),
    path("basket/remove/<int:product_id>/", views.basket_remove, name="basket_remove"),
    path("checkout/", views.checkout, name="shop_checkout"),
    path("checkout/create-intent/", views.create_stripe_intent, name="shop_create_intent"),
    path("checkout/confirm/", views.confirm_order, name="shop_confirm_order"),
    path("webhook/", views.stripe_webhook, name="shop_webhook"),




        # MANAGEMENT
    path("manage/", views.manage_products, name="shop_manage_products"),
    path("manage/add/", views.add_product, name="shop_add_product"),
    path("manage/edit/<int:product_id>/", views.edit_product, name="shop_edit_product"),
    path("manage/delete/<int:product_id>/", views.delete_product, name="shop_delete_product"),
    path("basket/", views.shop_basket, name="shop_basket"),
    path("orders/", views.shop_orders, name="shop_orders"),
    path("enable/", views.shop_enable, name="shop_enable"),
    path("disable/", views.shop_disable, name="shop_disable"),
    # Customer Orders
    path("orders/", views.my_orders, name="my_orders"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),

    # Staff Order Manager
    path("manage/orders/", views.manage_orders, name="manage_orders"),
    path("manage/orders/<int:order_id>/", views.manage_order_detail, name="manage_order_detail"),
    path("manage/orders/<int:order_id>/dispatch/", views.order_mark_dispatched, name="order_mark_dispatched"),
    path("manage/orders/<int:order_id>/collect/", views.order_mark_collected, name="order_mark_collected"),

]
