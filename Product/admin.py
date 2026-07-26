from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Product, ProductImage, Comment, Information,
    Size, Color, UsDiscount, Order, OrderItem, Discount,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "alt_text", "is_primary", "order")
    readonly_fields = ("created_at",)


class InformationInline(admin.StackedInline):
    model = Information
    extra = 1
    fields = ("text", "order")
    readonly_fields = ("created_at",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "like_count", "comment_count")
    list_filter = ("size", "color")
    search_fields = ("title", "description", "slug")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-id",)
    inlines = [ProductImageInline, InformationInline]

    @admin.display(description="Likes")
    def like_count(self, obj):
        return obj.likes.count()

    @admin.display(description="Approved comments")
    def comment_count(self, obj):
        return obj.comments.filter(is_approved=True).count()


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "alt_text", "is_primary", "order")
    list_filter = ("is_primary",)
    search_fields = ("product__title", "alt_text")


@admin.register(Information)
class InformationAdmin(admin.ModelAdmin):
    list_display = ("product", "text", "order")
    list_filter = ("product",)
    search_fields = ("text",)


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "text_short", "is_approved", "created_at")
    list_filter = ("is_approved", "created_at")
    list_editable = ("is_approved",)
    search_fields = ("user__phone", "user__full_name", "product__title", "text")
    actions = ["approve_comments", "reject_comments"]

    @admin.display(description="Comment text")
    def text_short(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text

    @admin.action(description="Approve selected comments")
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description="Reject selected comments")
    def reject_comments(self, request, queryset):
        queryset.update(is_approved=False)


class OrderItemInline(admin.StackedInline):
    model = OrderItem
    extra = 1
    readonly_fields = ("price",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total_price", "is_paid", "item_count", "created_at")
    list_filter = ("is_paid", "created_at")
    search_fields = ("user__phone", "user__full_name", "id")
    readonly_fields = ("total_price", "created_at")
    inlines = [OrderItemInline]

    @admin.display(description="Items")
    def item_count(self, obj):
        return obj.items.count()


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("name", "discount", "quantity", "is_active", "valid_from", "valid_until")
    list_filter = ("is_active",)
    search_fields = ("name",)
    readonly_fields = ("created_at",)


@admin.register(UsDiscount)
class UsDiscountAdmin(admin.ModelAdmin):
    list_display = ("user", "discount")
    list_filter = ("discount",)
    search_fields = ("user__phone", "user__full_name", "discount__name")
