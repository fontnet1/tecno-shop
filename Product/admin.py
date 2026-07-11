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

@admin.register(Information)
class InformationAdmin(admin.ModelAdmin):
    list_display = ('product', 'txte', 'order')
    list_filter = ('product',)



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'like_count', )
    list_filter = ('size', 'color',)
    search_fields = ('title', 'description')
    ordering = ('id','price',)
    inlines = [ProductImageInline, InformationInline]


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('title',)


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('title',)



from django.contrib import admin
from .models import Product, ProductImage, Comment, Information, Size, Color, ProductLike


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'order')
    readonly_fields = ('created_at',)


class InformationInline(admin.TabularInline):
    model = Information
    extra = 1
    fields = ('txte', 'order')




    def like_count(self, obj):
        return obj.likes.count()
    like_count.short_description = 'لایک‌ها'

    def comment_count(self, obj):
        return obj.comments.filter(is_approved=True).count()
    comment_count.short_description = 'نظرات تایید شده'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'text_short', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'created_at')
    list_editable = ('is_approved',)
    search_fields = ('user__username', 'product__title', 'text')
    actions = ['approve_comments', 'reject_comments']

    def text_short(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_short.short_description = 'متن نظر'

    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
    approve_comments.short_description = 'تایید نظرات انتخاب شده'

    def reject_comments(self, request, queryset):
        queryset.update(is_approved=False)
    reject_comments.short_description = 'رد نظرات انتخاب شده'





