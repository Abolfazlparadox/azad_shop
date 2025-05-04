# comment/forms.py

from django import forms
from comment.models import Comment

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content', 'rating']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'دیدگاه شما'
            }),
            'rating': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'content': 'دیدگاه شما',
            'rating': 'امتیاز',
        }
