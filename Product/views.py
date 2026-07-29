import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST, require_http_methods
from django.views.generic import ListView, DetailView, TemplateView

from . import cart
from .cart import Cart
from .forms import CommentForm
from .models import (
    Product, Comment, ProductLike, CommentLike,
    Color, Size, Category,
    Order, OrderItem, Discount, UsDiscount,
)
from Account.models import AddAddress

logger = logging.getLogger(__name__)

# Maximum allowed quantity per cart line / order item
MAX_QUANTITY = 100
SHIPPING_COST = Decimal("10.00")


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
    Prevents Open Redirect attacks.
    """
    referer = request.META.get("HTTP_REFERER", "")
    if referer:
        if request.get_host() in referer:
            return redirect(referer)
    return redirect(fallback_url_name)


# ─── Navbar Partial (dynamic cart/like counts) ──────────────────
class NavbarPartialView(TemplateView):
    template_name = "includs/Navbar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categoris"] = Category.objects.all()

        # Cart count
        cart = Cart(self.request)
        context["cart_count"] = len(cart)

        # Like count
        if self.request.user.is_authenticated:
            context["like_count"] = ProductLike.objects.filter(
                user=self.request.user
            ).count()
        else:
            context["like_count"] = 0

        return context


# ─── Product List ──────────────────────────────────────────────────
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


# ─── Product List by Category (slug-based) ────────────────────────
class ProductListByCategoryView(ListView):
    model = Product
    template_name = "Product/shop.html"
    context_object_name = "products"
    paginate_by = 9

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        category = get_object_or_404(Category, slug=slug)

        queryset = (
            Product.objects
            .filter(category=category)
            .prefetch_related("images", "color", "size")
            .annotate(like_count_annot=Count("likes"))
        )

        # Also include sub-category products
        sub_ids = category.subs.values_list("id", flat=True)
        if sub_ids:
            queryset = (
                Product.objects
                .filter(Q(category=category) | Q(category_id__in=sub_ids))
                .prefetch_related("images", "color", "size")
                .annotate(like_count_annot=Count("likes"))
            )

        return queryset.distinct().order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get("slug")
        context["current_category"] = get_object_or_404(Category, slug=slug)
        context["colors"] = Color.objects.all()
        context["sizes"] = Size.objects.all()
        return context


# ─── Product Detail ─────────────────────────────────────────────────
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
            # Pre-compute liked comment IDs for template
            comment_ids = list(context["comments"].values_list("id", flat=True))
            reply_ids = []
            for c in context["comments"]:
                reply_ids.extend(c.replies.values_list("id", flat=True))
            all_comment_ids = comment_ids + reply_ids
            context["liked_comment_ids"] = set(
                CommentLike.objects.filter(
                    comment_id__in=all_comment_ids,
                    user=self.request.user,
                ).values_list("comment_id", flat=True)
            )
        else:
            context["is_liked"] = False
            context["liked_comment_ids"] = set()

        # Related products — prefetch BEFORE slice
        context["related_products"] = (
            Product.objects.filter(
                color__in=self.object.color.all()
            )
            .exclude(id=self.object.id)
            .distinct()
            .prefetch_related("images")
            .annotate(like_count_annot=Count("likes"))[:4]
        )

        return context


# ─── Order Creation (POST-only) ──────────────────────────────────
@method_decorator(login_required, name="dispatch")
@method_decorator(require_POST, name="dispatch")
class OrderCreationsView(View):
    def post(self, request):
        cart = Cart(request)
        if len(cart) == 0:
            messages.error(request, "Your cart is empty.")
            return redirect("products:cart_detail")

        # Validate product existence
        for item in cart:
            if not Product.objects.filter(id=item["product_id"]).exists():
                messages.error(request, f'Product "{item["title"]}" no longer exists and was removed from your cart.')
                cart.remove(item["key"])

        if len(cart) == 0:
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


# ─── Order Detail ─────────────────────────────────────────────────
@method_decorator(login_required, name="dispatch")
class OrderDetail(View):
    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.prefetch_related("items__product__images"),
            id=pk,
            user=request.user,
        )
        return render(request, "Product/order_detale.html", {"order": order})


# ─── Order List ───────────────────────────────────────────────────
@method_decorator(login_required, name="dispatch")
class OrderListView(ListView):
    model = Order
    template_name = "Product/orders.html"
    context_object_name = "orders"
    paginate_by = 10

    def get_queryset(self):
        return (
            Order.objects
            .filter(user=self.request.user)
            .prefetch_related("items__product__images")
            .order_by("-created_at")
        )


# ─── Apply Discount ───────────────────────────────────────────────
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

        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order.id)
            discount_code = Discount.objects.select_for_update().get(id=discount_code.id)

            if discount_code.quantity <= 0 or not discount_code.is_valid():
                messages.error(request, "Coupon expired.")
                return redirect("products:order_detail", pk)

            already_used = UsDiscount.objects.filter(
                user=request.user, discount=discount_code
            ).exists()
            if already_used:
                messages.error(request, "You have already used this coupon.")
                return redirect("products:order_detail", pk)

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


# ─── Pay Order ────────────────────────────────────────────────────
@method_decorator(login_required, name="dispatch")
@method_decorator(require_POST, name="dispatch")
class PayOrderView(View):
    """Mark order as paid and attach selected address."""

    def post(self, request, pk):
        order = get_object_or_404(Order, id=pk, user=request.user)

        if order.is_paid:
            messages.warning(request, "This order has already been paid.")
            return redirect("products:order_detail", pk)

        # Attach address if provided
        address_id = request.POST.get("address_id")
        if address_id:
            address = AddAddress.objects.filter(id=address_id, user=request.user).first()
            if address:
                order.address = address

        order.is_paid = True
        order.save(update_fields=["is_paid", "address"])
        messages.success(request, "Order paid successfully!")
        return redirect("products:order_detail", pk)


# ─── Comments ──────────────────────────────────────────────────────
@login_required
@require_POST
def add_comment(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.product = product
        comment.user = request.user

        # Handle reply (parent comment)
        parent_id = request.POST.get("parent", "")
        if parent_id:
            try:
                parent_id = int(parent_id)
                parent = Comment.objects.filter(
                    pk=parent_id, product=product
                ).first()
                if parent:
                    comment.parent = parent
            except (ValueError, TypeError):
                pass

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


# ─── Like ──────────────────────────────────────────────────────────
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


# ─── Comment Like (AJAX) ──────────────────────────────────────────
@login_required
@require_POST
def toggle_comment_like(request, comment_id):
    """Toggle like on a comment. Returns JSON for AJAX requests."""
    comment = get_object_or_404(Comment, pk=comment_id)
    like, created = CommentLike.objects.get_or_create(
        comment=comment, user=request.user
    )
    if not created:
        like.delete()
        is_liked = False
    else:
        is_liked = True

    like_count = comment.likes.count()

    return JsonResponse({
        "is_liked": is_liked,
        "like_count": like_count,
    })


# ─── Cart ──────────────────────────────────────────────────────────
@require_POST
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart = Cart(request)

    quantity = _parse_int(request.POST.get("quantity", 1), default=1)
    color_id = request.POST.get("color") or None
    size_id = request.POST.get("size") or None

    # Validate that the chosen color/size belong to this product
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
    return render(request, "Product/cart.html", {
        "cart": cart,
        "shipping_cost": SHIPPING_COST,
    })


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


# ─── Custom 404 ────────────────────────────────────────────────────
def custom_404(request, exception):
    return render(request, "Product/404.html", status=404)
