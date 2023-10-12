from urllib.parse import urlparse

from dal import autocomplete
from django import forms
from django.contrib.auth import get_user_model, settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse_lazy

from .models import Category, Comment, ContentInList, LuvList, Pin, Post, Repost, Say

User = get_user_model()


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "content", "comments_enabled", "categories"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Post title..."}),
            "content": forms.Textarea(
                attrs={
                    "placeholder": "What do you want to share?",
                    "rows": 20,
                    "id": "text-input",
                }
            ),
            "categories": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("write:category-autocomplete"),
            ),
        }

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields["title"].label = ""
        self.fields["content"].label = ""
        self.fields["comments_enabled"].label = "Enable comments"
        self.fields[
            "categories"
        ].help_text = "Posts in categories appear only on their respective category pages, not in the general post list."


class SayForm(forms.ModelForm):
    class Meta:
        model = Say
        fields = ["content", "comments_enabled"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "placeholder": "What's on your mind?",
                    "id": "text-input",
                },
            ),
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
            "title": forms.TextInput(attrs={"placeholder": "Pin title..."}),
            "url": forms.TextInput(attrs={"placeholder": "https://www.example.com"}),
            "content": forms.Textarea(
                attrs={
                    "placeholder": "What do you want to share?",
                    "id": "text-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super(PinForm, self).__init__(*args, **kwargs)
        self.fields["title"].label = ""
        self.fields["url"].label = ""
        self.fields["content"].label = ""
        self.fields["comments_enabled"].label = "Enable comments"


class CommentForm(forms.ModelForm):
    content = forms.CharField(widget=forms.Textarea(attrs={"id": "text-input"}))

    class Meta:
        model = Comment
        fields = ["content"]

    def __init__(self, *args, **kwargs):
        super(CommentForm, self).__init__(*args, **kwargs)
        self.fields["content"].label = ""


class ActivityFeedSayForm(SayForm):
    content = forms.CharField(
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "What's on your mind?", "id": "text-input"}
        )
    )

    def __init__(self, *args, **kwargs):
        super(ActivityFeedSayForm, self).__init__(*args, **kwargs)
        self.fields["comments_enabled"].initial = True
        self.fields["comments_enabled"].label = "Enable comments"


class RepostForm(forms.ModelForm):
    content = forms.CharField(widget=forms.Textarea(attrs={"id": "text-input"}))

    class Meta:
        model = Repost
        fields = ["content", "comments_enabled"]

    def __init__(self, *args, **kwargs):
        super(RepostForm, self).__init__(*args, **kwargs)
        self.fields["content"].label = ""
        self.fields["comments_enabled"].label = "Enable comments"
        self.fields["content"].required = False


class LuvListForm(forms.ModelForm):
    class Meta:
        model = LuvList
        fields = [
            "title",
            "description",
            "source",
            "wikipedia",
        ]


class ContentInListForm(forms.ModelForm):
    content_url = forms.URLField()
    comment = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "What do you say about it?",
                "id": "text-input",
            }
        )
    )

    class Meta:
        model = ContentInList
        fields = ["content_url", "order", "comment"]
        exclude = ["luv_list"]

    def clean_content_url(self):
        content_url = self.cleaned_data.get("content_url")
        if not content_url:  # if the field is empty, just return it
            return content_url
        # Parse the URL and get only the path
        path = urlparse(content_url).path
        # Split the path based on "/"
        content_parts = path.strip("/").split("/")
        if len(content_parts) == 3:
            app_label, model_name, object_id = content_parts
        elif len(content_parts) == 5:
            app_label, _, _, model_name, object_id = content_parts
        else:
            raise forms.ValidationError("Invalid Content URL")

        try:
            content_type = ContentType.objects.get(
                app_label=app_label, model=model_name
            )
            content_object = content_type.get_object_for_this_type(pk=object_id)
        except (ContentType.DoesNotExist, ObjectDoesNotExist):
            raise forms.ValidationError("Content does not exist")

        self.instance.content_object = (
            content_object  # save the content instance directly
        )
        return content_url

    def clean(self):
        cleaned_data = super().clean()
        content_url = cleaned_data.get("content_url")
        if not content_url:  # if the content_url field is empty
            self.cleaned_data["DELETE"] = True  # mark the form instance for deletion
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super(ContentInListForm, self).__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.content_object:
            content_url = self.instance.content_object.get_absolute_url()
            self.fields["content_url"].label = "URL"
            self.fields["content_url"].initial = f"{settings.ROOT_URL}{content_url}"
            self.fields["content_url"].required = False
        else:
            self.fields["content_url"].required = False  # Add this line

        self.fields["order"].required = False
        self.fields["comment"].required = False
        self.fields["content_url"].label = "URL"


ContentInListFormSet = forms.inlineformset_factory(
    LuvList,
    ContentInList,
    form=ContentInListForm,
    extra=1,
    can_delete=True,
    widgets={
        "content_url": forms.URLInput(attrs={"required": False}),
        "order": forms.NumberInput(attrs={"required": False}),
    },
)
