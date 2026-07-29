from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.conf import settings
from django.utils.text import slugify
import os

from Account.models import User, AddAddress


class Category(models.Model):
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="subs")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "category"
            slug = base
            n = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Size(models.Model):
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title


class Color(models.Model):
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title


class Information(models.Model):
    product = models.ForeignKey(
        "Product",
        on_delete=models.CASCADE,
        related_name="informations"
    )
    text = models.CharField(max_length=80, default="Information is up to 80 characters long.")
    order = models.PositiveIntegerField(default=0, verbose_name="Display order")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text[:30]


class Product(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="Category",
    )
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    size = models.ManyToManyField(Size, related_name="products", blank=True)
    color = models.ManyToManyField(Color, related_name="products", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto-generate slug from title if not provided (keep it unique)
        if not self.slug:
            base = slugify(self.title) or "product"
            slug = base
            n = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("products:product-detail", kwargs={"pk": self.pk})

    def like_count(self):
        return self.likes.count()


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=200, blank=True, verbose_name="Alternative text")
    is_primary = models.BooleanField(default=False, verbose_name="Primary image")
    order = models.PositiveIntegerField(default=0, verbose_name="Display order")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Product image"
        verbose_name_plural = "Product images"
        ordering = ["order"]

    def __str__(self):
        return f"{self.product.title}"


# Delete image file when ProductImage is deleted
@receiver(post_delete, sender=ProductImage)
def delete_image_file(sender, instance, **kwargs):
    if instance.image and instance.image.name:
        try:
            if os.path.isfile(instance.image.path):
                os.remove(instance.image.path)
        except (ValueError, OSError):
            pass


# Delete old image file when ProductImage is updated
@receiver(pre_save, sender=ProductImage)
def delete_old_image(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old_file = ProductImage.objects.get(pk=instance.pk).image
    except ProductImage.DoesNotExist:
        return
    if old_file and old_file.name and old_file != instance.image:
        try:
            if os.path.isfile(old_file.path):
                os.remove(old_file.path)
        except (ValueError, OSError):
            pass


class Comment(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    text = models.TextField(max_length=2000)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.product.title}"


class ProductLike(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("product", "user")

    def __str__(self):
        return f"{self.user} liked {self.product.title}"


class CommentLike(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("comment", "user")


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    created_at = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Total"
    )
    is_paid = models.BooleanField(default=False, verbose_name="Paid")
    address = models.ForeignKey(
        AddAddress,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Shipping Address",
    )

    def __str__(self):
        phone = getattr(self.user, "phone", None) if self.user_id else None
        return f"Order #{self.id} - {phone or 'unknown'}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    size = models.ForeignKey(
        Size, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="sizes"
    )
    color = models.ForeignKey(
        Color, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="colors"
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity")
    price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Price"
    )

    def __str__(self):
        return f"{self.product} x {self.quantity}"


class Discount(models.Model):
    name = models.CharField(max_length=50, verbose_name="Name", unique=True)
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity")
    discount = models.PositiveIntegerField(
        default=0,
        verbose_name="Discount (%)",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True, verbose_name="Active")

    def __str__(self):
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.valid_from and self.valid_until and self.valid_from > self.valid_until:
            raise ValidationError("'valid_from' must be earlier than 'valid_until'.")

    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        return (
            self.is_active
            and self.quantity > 0
            and self.valid_from <= now <= self.valid_until
        )


class UsDiscount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="used_discounts")
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name="used_by")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "discount"],
                name="unique_user_discount",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.discount}"
