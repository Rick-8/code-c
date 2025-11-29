from django.urls import path
from . import views

urlpatterns = [
    path("", views.shop_home, name="shop_home"),
    path("product/<int:product_id>/", views.product_detail, name="shop_product_detail"),

        # MANAGEMENT
    path("manage/", views.manage_products, name="shop_manage_products"),
    path("manage/add/", views.add_product, name="shop_add_product"),
    path("manage/edit/<int:product_id>/", views.edit_product, name="shop_edit_product"),
    path("manage/delete/<int:product_id>/", views.delete_product, name="shop_delete_product"),
    path("basket/", views.shop_basket, name="shop_basket"),
    path("orders/", views.shop_orders, name="shop_orders"),
    path("enable/", views.shop_enable, name="shop_enable"),
    path("disable/", views.shop_disable, name="shop_disable"),

]
