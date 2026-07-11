from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from tecno_shop import settings
import os


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
    txte = models.CharField(max_length=80, default="Information is up to 80 characters long.")
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0, verbose_name='Information order')

    def __str__(self):
        return self.txte[:30]


class Product(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    size = models.ManyToManyField(Size, related_name='sizes', blank=True)
    color = models.ManyToManyField(Color, related_name='colors', blank=True)

    def __str__(self):
        return self.title

    def like_count(self):
        return self.likes.count()


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    alt = models.CharField(max_length=255, blank=True)
    alt_text = models.CharField(max_length=200, blank=True, verbose_name='Alternative text')
    is_primary = models.BooleanField(default=False, verbose_name='Original image')
    order = models.PositiveIntegerField(default=0, verbose_name='Display order')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.title}"

    class Meta:
        verbose_name = 'Product image'
        verbose_name_plural = 'Product images'
        ordering = ['order']


# ✅ پاک کردن فایل وقتی عکس حذف میشه
@receiver(post_delete, sender=ProductImage)
def delete_image_file(sender, instance, **kwargs):
    if instance.image and os.path.isfile(instance.image.path):
        os.remove(instance.image.path)


# ✅ پاک کردن فایل قدیمی وقتی عکس جایگزین میشه
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
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    text = models.TextField()
    is_approved = models.BooleanField(default=False)  # مدیریت نظرات
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.product.title}"


class ProductLike(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product', 'user')  # هر کاربر فقط یه بار لایک کنه

    def __str__(self):
        return f"{self.user} liked {self.product.title}"


class CommentLike(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('comment', 'user')


class CartItem(models.Model):
    session_key = models.CharField(max_length=40)  # کلید سشن
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True)
    size = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('session_key', 'product', 'color', 'size')

    def total_price(self):
        return self.product.price * self.quantity