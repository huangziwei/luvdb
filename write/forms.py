from django import forms

from .models import Post, Say


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "content"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Title..."}),
            "content": forms.Textarea(
                attrs={"placeholder": "What do you want to share?"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields["title"].label = ""
        self.fields["content"].label = ""


class SayForm(forms.ModelForm):
    class Meta:
        model = Say
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={"placeholder": "What's on your mind?"}),
        }

    def __init__(self, *args, **kwargs):
        super(SayForm, self).__init__(*args, **kwargs)
        self.fields["content"].label = ""
