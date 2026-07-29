from django.shortcuts import render
from django.views.generic import TemplateView
from django.db.models import Count

from Product.models import Product, Category, ProductImage


class HomePageView(TemplateView):
    template_name = "home/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Categories (only top-level, with product counts)
        context["categories"] = (
            Category.objects
            .filter(parent__isnull=True)
            .annotate(product_count=Count("products"))
            .prefetch_related("subs")
        )

        # Featured products — annotated for like count, with images
        context["featured_products"] = (
            Product.objects
            .prefetch_related("images")
            .annotate(like_count_annot=Count("likes"))
            .order_by("-created_at")[:8]
        )

        # Recent products (same as featured but most recent)
        context["recent_products"] = (
            Product.objects
            .prefetch_related("images")
            .annotate(like_count_annot=Count("likes"))
            .order_by("-created_at")[:8]
        )

        return context
