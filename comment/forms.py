from django import forms
from .models import Comment

class CommentForm(forms.ModelForm):
    parent = forms.IntegerField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Comment
        fields = ['content', 'rating']  # ← remove 'parent' from here
        widgets = {
            'content': forms.Textarea(attrs={'rows':4, 'class':'form-control'}),
            'rating': forms.Select(attrs={'class':'form-select'}),
        }
