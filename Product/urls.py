from django.urls import path
from . import views
app_name = 'products'
urlpatterns = [
    path('<int:pk>/',views.ProductDetailView.as_view(),name='product-detail'),
    path('',views.ProductListView.as_view(),name='product_list'),
    path('add_to_cart/<int:pk>/',views.add_to_cart,name='add_to_cart'),
    path('toggle_like/<int:pk>/', views.toggle_like , name='toggle_like'),
    path('add_comment/<int:pk>/', views.add_comment, name='add_comment'),
    path('cart_detail',views.cart_detail,name='cart_detail'),
    path('cart_update', views.cart_update, name='cart_update'),
    path('cart_remove/<str:key>/', views.cart_remove, name='cart_remove'),
    path('cart_clear', views.cart_clear, name='cart_clear'),

]