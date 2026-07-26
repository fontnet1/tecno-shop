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
                "maxlength": "2000",
            }),
        }
