from decimal import Decimal

from .models import Product


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get("cart")
        if not cart:
            cart = self.session["cart"] = {}

    def add(self, product_id, quantity=1, color_id=None, size_id=None):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return

        key = f"{product_id}-{color_id or ''}-{size_id or ''}"

        if key in self.session["cart"]:
            self.session["cart"][key]["quantity"] += quantity
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
        if key in self.session["cart"]:
            if quantity <= 0:
                self.remove(key)
            else:
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
        return sum(item["quantity"] for item in self.session["cart"].values())

    def get_total_price(self):
        return sum(
            Decimal(item["price"]) * item["quantity"]
            for item in self.session["cart"].values()
        )

    def __iter__(self):
        for key, item in self.session["cart"].items():
            item["key"] = key
            item["total"] = str(Decimal(item["price"]) * item["quantity"])
            yield item