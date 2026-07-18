from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.conf import settings
import os

from Account.models import User


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
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    size = models.ManyToManyField(Size, related_name="products", blank=True)
    color = models.ManyToManyField(Color, related_name="products", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

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
    if instance.image and os.path.isfile(instance.image.path):
        os.remove(instance.image.path)


# Delete old image file when ProductImage is updated
@receiver(pre_save, sender=ProductImage)
def delete_old_image(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old_file = ProductImage.objects.get(pk=instance.pk).image
    except ProductImage.DoesNotExist:
        return
    if old_file and old_file != instance.image:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)


class Comment(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    text = models.TextField()
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="item")
    adress = models.TextField(max_length=300, verbose_name="Adress")
    email = models.EmailField(max_length=300, verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Phone")
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False, verbose_name="Paid")
    def __str__(self):
        return self.user.username



class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity")
    price = models.PositiveIntegerField(default=0, verbose_name="Price")