import logging

from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import Product, Comment, ProductLike, Color, Size
from .forms import CommentForm
from .cart import Cart

logger = logging.getLogger(__name__)


# ─── Product List ──────────────────────────────────────────
class ProductListView(ListView):
    model = Product
    template_name = "Product/shop.html"
    context_object_name = "products"
    paginate_by = 9

    def get_queryset(self):
        queryset = Product.objects.prefetch_related(
            "images", "likes", "color", "size"
        )

        q = self.request.GET.get("q")
        min_price = self.request.GET.get("min_price")
        max_price = self.request.GET.get("max_price")
        color = self.request.GET.get("color")
        size = self.request.GET.get("size")
        ordering = self.request.GET.get("ordering")

        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) | Q(description__icontains=q)
            )
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if color:
            queryset = queryset.filter(color__id=color)
        if size:
            queryset = queryset.filter(size__id=size)

        if ordering == "newest":
            queryset = queryset.order_by("-created_at")
        elif ordering == "cheapest":
            queryset = queryset.order_by("price")
        elif ordering == "expensive":
            queryset = queryset.order_by("-price")
        elif ordering == "popular":
            queryset = queryset.annotate(
                like_count=Count("likes")
            ).order_by("-like_count")
        else:
            queryset = queryset.order_by("-created_at")

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["colors"] = Color.objects.all()
        context["sizes"] = Size.objects.all()
        return context


# ─── Product Detail ────────────────────────────────────────
class ProductDetailView(DetailView):
    model = Product
    template_name = "Product/detail.html"
    context_object_name = "product"

    def get_queryset(self):
        return Product.objects.prefetch_related(
            "images", "likes", "color", "size", "informations"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["comments"] = (
            self.object.comments.filter(
                is_approved=True,
                parent__isnull=True,
            )
            .select_related("user")
            .prefetch_related("replies__user")
        )

        if self.request.user.is_authenticated:
            context["is_liked"] = ProductLike.objects.filter(
                product=self.object, user=self.request.user
            ).exists()
        else:
            context["is_liked"] = False

        context["related_products"] = (
            Product.objects.filter(
                color__in=self.object.color.all()
            )
            .exclude(id=self.object.id)
            .distinct()[:4]
            .prefetch_related("images", "likes")
        )

        return context


# ─── Comments ──────────────────────────────────────────────
@login_required
def add_comment(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.product = product
            comment.user = request.user
            comment.save()
            messages.success(
                request,
                "Your comment has been registered and will be displayed after approval."
            )
        else:
            messages.error(request, "Please fill out the form correctly.")

    return redirect("products:product-detail", pk=pk)


@login_required
def comment_reply(request, pk, comment_id):
    product = get_object_or_404(Product, pk=pk)
    parent = get_object_or_404(Comment, pk=comment_id, product=product)

    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.product = product
            reply.user = request.user
            reply.parent = parent
            reply.save()
            messages.success(request, "Your reply has been recorded.")

    return redirect("products:product-detail", pk=pk)


# ─── Like ──────────────────────────────────────────────────
@login_required
@require_POST
def toggle_like(request, pk):
    product = get_object_or_404(Product, pk=pk)

    like, created = ProductLike.objects.get_or_create(
        product=product, user=request.user
    )

    if not created:
        like.delete()
        is_liked = False
    else:
        is_liked = True

    like_count = product.likes.count()

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "is_liked": is_liked,
            "like_count": like_count,
        })

    return redirect("products:product-detail", pk=pk)


# ─── Cart ──────────────────────────────────────────────────
@require_POST
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart = Cart(request)

    quantity = int(request.POST.get("quantity", 1))
    color_id = request.POST.get("color") or None
    size_id = request.POST.get("size") or None

    cart.add(
        product_id=product.id,
        quantity=quantity,
        color_id=color_id,
        size_id=size_id,
    )
    messages.success(request, f"{product.title} added to cart.")
    return redirect(request.META.get("HTTP_REFERER", "products:product_list"))


def cart_detail(request):
    cart = Cart(request)
    return render(request, "Product/cart.html", {"cart": cart})


@require_POST
def cart_update(request):
    cart = Cart(request)
    for key, quantity in request.POST.items():
        if key.startswith("qty-"):
            item_key = key[4:]
            cart.update(item_key, int(quantity))
    messages.success(request, "Shopping cart updated.")
    return redirect("products:cart_detail")


@require_POST
def cart_remove(request, key):
    cart = Cart(request)
    cart.remove(key)
    messages.success(request, "The product was removed from the shopping cart.")
    return redirect("products:cart_detail")


@require_POST
def cart_clear(request):
    cart = Cart(request)
    cart.clear()
    messages.success(request, "Shopping cart cleared.")
    return redirect("products:cart_detail")