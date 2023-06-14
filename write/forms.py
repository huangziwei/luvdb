from django import forms

from .models import Comment, Pin, Post, Repost, Say


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "content", "comments_enabled"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Title..."}),
            "content": forms.Textarea(
                attrs={
                    "placeholder": "What do you want to share?",
                    "rows": 20,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields["title"].label = ""
        self.fields["content"].label = ""
        self.fields["comments_enabled"].label = "Enable comments"


class SayForm(forms.ModelForm):
    class Meta:
        model = Say
        fields = ["content", "comments_enabled"]
        widgets = {
            "content": forms.Textarea(attrs={"placeholder": "What's on your mind?"}),
        }

    def __init__(self, *args, **kwargs):
        super(SayForm, self).__init__(*args, **kwargs)
        self.fields["content"].label = ""
        self.fields["comments_enabled"].label = "Enable comments"


class PinForm(forms.ModelForm):
    class Meta:
        model = Pin
        fields = ["title", "url", "content", "comments_enabled"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Title..."}),
            "url": forms.TextInput(attrs={"placeholder": "https://www.example.com"}),
            "content": forms.Textarea(
                attrs={"placeholder": "What do you want to share?"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super(PinForm, self).__init__(*args, **kwargs)
        self.fields["title"].label = ""
        self.fields["url"].label = ""
        self.fields["content"].label = ""
        self.fields["comments_enabled"].label = "Enable comments"


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]

    def __init__(self, *args, **kwargs):
        super(CommentForm, self).__init__(*args, **kwargs)
        self.fields["content"].label = ""


class ActivityFeedSayForm(SayForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "What's on your mind?"})
    )

    def __init__(self, *args, **kwargs):
        super(ActivityFeedSayForm, self).__init__(*args, **kwargs)
        self.fields["comments_enabled"].initial = True
        self.fields["comments_enabled"].label = "Enable comments"


class RepostForm(forms.ModelForm):
    class Meta:
        model = Repost
        fields = ["content"]

    def __init__(self, *args, **kwargs):
        super(RepostForm, self).__init__(*args, **kwargs)
        self.fields["content"].label = ""
