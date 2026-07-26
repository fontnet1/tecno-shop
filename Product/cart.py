from decimal import Decimal, InvalidOperation

from .models import Product

# Hard cap so a malicious/buggy client can't bloat the session
MAX_QUANTITY = 100


class Cart:
    """Session-based shopping cart. All inputs are validated before being stored."""

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get("cart")
        if not cart:
            cart = self.session["cart"] = {}

    def add(self, product_id, quantity=1, color_id=None, size_id=None):
        try:
            product = Product.objects.get(id=product_id)
        except (Product.DoesNotExist, ValueError):
            return

        # Clamp quantity to a sane range
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            quantity = 1
        if quantity < 1:
            quantity = 1
        if quantity > MAX_QUANTITY:
            quantity = MAX_QUANTITY

        # Sanitize optional ids (defensive; the view also checks them)
        color_id = self._sanitize_id(color_id)
        size_id = self._sanitize_id(size_id)

        key = f"{product_id}-{color_id or ''}-{size_id or ''}"

        existing = self.session["cart"].get(key)
        if existing:
            new_qty = int(existing.get("quantity", 0)) + quantity
            if new_qty > MAX_QUANTITY:
                new_qty = MAX_QUANTITY
            existing["quantity"] = new_qty
        else:
            primary_image = product.images.filter(is_primary=True).first()
            self.session["cart"][key] = {
                "product_id": product.id,
                "title": product.title,
                "price": str(product.price),
                "image": primary_image.image.url if primary_image else "",
                "quantity": quantity,
                "color_id": color_id,
                "size_id": size_id,
            }
        self.session.modified = True

    def update(self, key, quantity):
        """Update quantity for an existing cart line. Removes the line if qty <= 0."""
        if key not in self.session["cart"]:
            return
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return
        if quantity <= 0:
            self.remove(key)
            return
        if quantity > MAX_QUANTITY:
            quantity = MAX_QUANTITY
        self.session["cart"][key]["quantity"] = quantity
        self.session.modified = True

    def remove(self, key):
        if key in self.session["cart"]:
            del self.session["cart"][key]
            self.session.modified = True

    def clear(self):
        self.session["cart"] = {}
        self.session.modified = True

    def __len__(self):
        return sum(item.get("quantity", 0) for item in self.session["cart"].values())

    def get_total_price(self):
        total = Decimal(0)
        for item in self.session["cart"].values():
            try:
                total += Decimal(item["price"]) * int(item.get("quantity", 0))
            except (InvalidOperation, TypeError, ValueError, KeyError):
                # Skip malformed lines instead of crashing the whole cart
                continue
        return total

    def __iter__(self):
        for key, item in self.session["cart"].items():
            # Don't mutate the session-stored dict in-place; return a copy
            line = dict(item)
            line["key"] = key
            try:
                line["total"] = str(Decimal(line["price"]) * int(line.get("quantity", 0)))
            except (InvalidOperation, TypeError, ValueError):
                line["total"] = "0"
            yield line

    # ─── helpers ────────────────────────────────────────────
    @staticmethod
    def _sanitize_id(raw):
        """Return an int id or None. Rejects anything that isn't a positive int."""
        if raw is None or raw == "":
            return None
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None
