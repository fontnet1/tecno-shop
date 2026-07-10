from django.contrib import admin
from .models import Product, ProductImage, Size, Color,Information


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'order')
    readonly_fields = ('created_at',)

class InformationInline(admin.StackedInline):
    model = Information
    extra = 1
    fields = ('txte', 'order',)
    readonly_fields = ('created_at',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'price','id')
    list_filter = ('size', 'color',)
    search_fields = ('title', 'description')
    ordering = ('id','price',)
    search_fields=('title', 'description')
    inlines = [ProductImageInline, InformationInline]


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('title',)


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('title',)
