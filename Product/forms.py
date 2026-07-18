from django import forms
from .models import Product, Comment, ProductImage,Size,Color


from django import forms
from .models import Comment


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(attrs={
                "class": "w-full p-3 border rounded-lg resize-none",
                "rows": 4,
                "placeholder": "Write your review...",
            }),
        }


class ProductSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full p-3 border rounded-lg',
            'placeholder': 'جستجوی محصول...',
        })
    )
    min_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full p-3 border rounded-lg',
            'placeholder': 'حداقل قیمت',
        })
    )
    max_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full p-3 border rounded-lg',
            'placeholder': 'حداکثر قیمت',
        })
    )
    size = forms.ModelChoiceField(
        queryset=Size.objects.all(),
        required=False,
        empty_label='همه سایزها',
        widget=forms.Select(attrs={'class': 'w-full p-3 border rounded-lg'})
    )
    color = forms.ModelChoiceField(
        queryset=Color.objects.all(),
        required=False,
        empty_label='همه رنگ‌ها',
        widget=forms.Select(attrs={'class': 'w-full p-3 border rounded-lg'})
    )