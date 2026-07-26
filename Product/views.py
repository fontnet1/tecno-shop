import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST, require_http_methods
from django.views.generic import ListView, DetailView

from . import cart
from .cart import Cart
from .forms import CommentForm
from .models import (
    Product, Comment, ProductLike, Color, Size,
    Order, OrderItem, Discount, UsDiscount,
)

logger = logging.getLogger(__name__)

# Maximum allowed quantity per cart line / order item
MAX_QUANTITY = 100


def _parse_int(value, default=1, minimum=1, maximum=MAX_QUANTITY):
    """Safely parse int from untrusted input. Returns ``default`` on failure."""
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default
    if result < minimum:
        return minimum
    if maximum is not None and result > maximum:
        return maximum
    return result


def _safe_redirect_back(request, fallback_url_name="products:product_list"):
    """
    Redirect back to HTTP_REFERER but ONLY if it's a safe same-host URL.
    Prevents Open Redirect attacks where a malicious external Referer header
    could redirect the user to a third-party site.
    """
    referer = request.META.get("HTTP_REFERER", "")
    if referer:
        # Only allow same-host redirects
        if request.get_host() in referer:
            return redirect(referer)
    return redirect(fallback_url_name)


# ─── Product List ──────────────────────────────────────────
class ProductListView(ListView):
    model = Product
    template_name = "Product/shop.html"
    context_object_name = "products"
    paginate_by = 9

    def get_queryset(self):
        queryset = (
            Product.objects
            .prefetch_related("images", "color", "size")
            .annotate(like_count_annot=Count("likes"))
        )

        q = self.request.GET.get("q", "").strip()
        min_price = self.request.GET.get("min_price")
        max_price = self.request.GET.get("max_price")
        color = self.request.GET.get("color")
        size = self.request.GET.get("size")
        ordering = self.request.GET.get("ordering")

        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) | Q(description__icontains=q)
            )
        # Safe numeric filters
        if min_price:
            try:
                queryset = queryset.filter(price__gte=Decimal(min_price))
            except (InvalidOperation, TypeError):
                pass
        if max_price:
            try:
                queryset = queryset.filter(price__lte=Decimal(max_price))
            except (InvalidOperation, TypeError):
                pass
        if color:
            try:
                queryset = queryset.filter(color__id=int(color))
            except (TypeError, ValueError):
                pass
        if size:
            try:
                queryset = queryset.filter(size__id=int(size))
            except (TypeError, ValueError):
                pass

        # Whitelisted ordering prevents arbitrary SQL/order-by injection
        ordering_map = {
            "newest": "-created_at",
            "cheapest": "price",
            "expensive": "-price",
        }
        if ordering == "popular":
            queryset = queryset.order_by("-like_count_annot")
        else:
            queryset = queryset.order_by(ordering_map.get(ordering, "-created_at"))

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

        # ⚠ prefetch_related MUST come before slicing, otherwise the prefetch
        # is dropped and you'll get an N+1 query in the template.
        context["related_products"] = (
            Product.objects.filter(
                color__in=self.object.color.all()
            )
            .exclude(id=self.object.id)
            .distinct()
            .prefetch_related("images", "likes")[:4]
        )

        return context


# ─── Order Creation (POST-only to prevent CSRF via GET) ────
@method_decorator(login_required, name="dispatch")
@method_decorator(require_POST, name="dispatch")
class OrderCreationsView(View):
    def post(self, request):
        cart = Cart(request)
        if len(cart) == 0:
            messages.error(request, "Your cart is empty.")
            return redirect("products:cart_detail")

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                total_price=cart.get_total_price(),
            )
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product_id=item["product_id"],
                    quantity=item["quantity"],
                    color_id=item["color_id"],
                    price=item["price"],
                    size_id=item["size_id"],
                )
            cart.clear()
        return redirect("products:order_detail", order.id)


@method_decorator(login_required, name="dispatch")
class OrderDetail(View):
    def get(self, request, pk):
        order = get_object_or_404(Order, id=pk, user=request.user)
        return render(request, "Product/order_detale.html", {"order": order})


@method_decorator(login_required, name="dispatch")
class ApplyDiscountView(View):
    def post(self, request, pk):
        code = (request.POST.get("discount_code") or "").strip()
        if not code:
            messages.error(request, "Please enter a coupon code.")
            return redirect("products:order_detail", pk)

        order = get_object_or_404(Order, id=pk, user=request.user)
        discount_code = Discount.objects.filter(name=code).first()
        if not discount_code:
            messages.error(request, "Coupon code not found.")
            return redirect("products:order_detail", pk)

        if not discount_code.is_valid():
            messages.error(request, "Coupon expired or inactive.")
            return redirect("products:order_detail", pk)

        # Race-condition-safe block: lock the rows we are about to mutate
        with transaction.atomic():
            # Re-fetch both rows with a row-level lock
            order = Order.objects.select_for_update().get(id=order.id)
            discount_code = Discount.objects.select_for_update().get(id=discount_code.id)

            # Check again inside the lock (another request may have just used it)
            if discount_code.quantity <= 0 or not discount_code.is_valid():
                messages.error(request, "Coupon expired.")
                return redirect("products:order_detail", pk)

            already_used = UsDiscount.objects.filter(
                user=request.user, discount=discount_code
            ).exists()
            if already_used:
                messages.error(request, "You have already used this coupon.")
                return redirect("products:order_detail", pk)

            # Apply discount (clamped to >= 0 so price can never go negative)
            discount_amount = order.total_price * Decimal(discount_code.discount) / Decimal(100)
            new_total = order.total_price - discount_amount
            if new_total < 0:
                new_total = Decimal(0)
            order.total_price = new_total
            order.save()

            UsDiscount.objects.create(user=request.user, discount_id=discount_code.id)
            discount_code.quantity -= 1
            discount_code.save(update_fields=["quantity"])

        messages.success(request, "Coupon applied successfully.")
        return redirect("products:order_detail", pk)


# ─── Comments ──────────────────────────────────────────────
@login_required
@require_POST
def add_comment(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.product = product
        comment.user = request.user
        comment.save()
        messages.success(
            request,
            "Your comment has been registered and will be displayed after approval.",
        )
    else:
        messages.error(request, "Please fill out the form correctly.")
    return redirect("products:product-detail", pk=pk)


@login_required
@require_POST
def comment_reply(request, pk, comment_id):
    product = get_object_or_404(Product, pk=pk)
    parent = get_object_or_404(Comment, pk=comment_id, product=product)
    form = CommentForm(request.POST)
    if form.is_valid():
        reply = form.save(commit=False)
        reply.product = product
        reply.user = request.user
        reply.parent = parent
        reply.save()
        messages.success(request, "Your reply has been recorded.")
    else:
        messages.error(request, "Please fill out the form correctly.")
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

    quantity = _parse_int(request.POST.get("quantity", 1), default=1)
    color_id = request.POST.get("color") or None
    size_id = request.POST.get("size") or None

    # Validate that the chosen color/size actually belong to this product
    if color_id:
        if not product.color.filter(id=color_id).exists():
            messages.error(request, "Invalid color selected.")
            return _safe_redirect_back(request)
    if size_id:
        if not product.size.filter(id=size_id).exists():
            messages.error(request, "Invalid size selected.")
            return _safe_redirect_back(request)

    cart.add(
        product_id=product.id,
        quantity=quantity,
        color_id=color_id,
        size_id=size_id,
    )
    messages.success(request, f"{product.title} added to cart.")
    return _safe_redirect_back(request)


def cart_detail(request):
    cart = Cart(request)
    return render(request, "Product/cart.html", {"cart": cart})


@require_POST
def cart_update(request):
    cart = Cart(request)
    for key, quantity in request.POST.items():
        if key.startswith("qty-"):
            item_key = key[4:]
            qty = _parse_int(quantity, default=1)
            cart.update(item_key, qty)
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
