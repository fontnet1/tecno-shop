from django.shortcuts import render
from django.views.generic import DetailView
from django.views.generic import TemplateView

from Product.models import Product


class ProductDetailView(DetailView):
    model = Product
    context_object_name = 'product'
    template_name = 'Product/detail.html'