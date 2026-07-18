from django.urls import path
from . import views

app_name = "products"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="product_list"),
    path("<int:pk>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("add_to_cart/<int:pk>/", views.add_to_cart, name="add_to_cart"),
    path("toggle_like/<int:pk>/", views.toggle_like, name="toggle_like"),
    path("add_comment/<int:pk>/", views.add_comment, name="add_comment"),
    path("comment_reply/<int:pk>/<int:comment_id>/", views.comment_reply, name="comment_reply"),
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/update/", views.cart_update, name="cart_update"),
    path("cart/remove/<str:key>/", views.cart_remove, name="cart_remove"),
    path("cart/clear/", views.cart_clear, name="cart_clear"),
]