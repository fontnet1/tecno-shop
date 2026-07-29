from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="product_list"),
    path("category/<slug:slug>/", views.ProductListByCategoryView.as_view(), name="product_list_by_category"),
    path("<int:pk>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("navbar/", views.NavbarPartialView.as_view(), name="navbar"),

    path("add_to_cart/<int:pk>/", views.add_to_cart, name="add_to_cart"),
    path("toggle_like/<int:pk>/", views.toggle_like, name="toggle_like"),
    path("toggle_comment_like/<int:comment_id>/", views.toggle_comment_like, name="toggle_comment_like"),
    path("add_comment/<int:pk>/", views.add_comment, name="add_comment"),
    path(
        "comment_reply/<int:pk>/<int:comment_id>/",
        views.comment_reply,
        name="comment_reply",
    ),
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/update/", views.cart_update, name="cart_update"),
    path("cart/remove/<str:key>/", views.cart_remove, name="cart_remove"),
    path("cart/clear/", views.cart_clear, name="cart_clear"),
    path("order_detail/<int:pk>/", views.OrderDetail.as_view(), name="order_detail"),
    path("orders/", views.OrderListView.as_view(), name="order_list"),
    path("order/add/", views.OrderCreationsView.as_view(), name="order_add"),
    path("order/pay/<int:pk>/", views.PayOrderView.as_view(), name="order_pay"),
    path("apply_discount/<int:pk>/", views.ApplyDiscountView.as_view(), name="apply_discount"),
]
