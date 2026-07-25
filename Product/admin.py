from django.contrib import admin
from .models import (
    Product, ProductImage, Comment, Information,
    Size, Color, UsDiscount,Order,OrderItem,Discount
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
    search_fields = ("title", "description")
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


@admin.register(Information)
class InformationAdmin(admin.ModelAdmin):
    list_display = ("product", "text", "order")
    list_filter = ("product",)


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ("title",)


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ("title",)


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

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("user",)
    inlines = [OrderItemInline]

@admin.register(Discount)
class OrderAdmin(admin.ModelAdmin):
    list_display = ( "discount","quantity","name" )
@admin.register(UsDiscount)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("user", )