from urllib.parse import urlparse

import auto_prefetch
from dal import autocomplete
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse, reverse_lazy

from .models import (
    Album,
    Comment,
    ContentInList,
    LuvList,
    Photo,
    Pin,
    Post,
    Repost,
    Say,
)

User = get_user_model()


class PostForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = Post
        fields = ["title", "content", "comments_enabled", "projects", "share_to_feed"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Post title..."}),
            "content": forms.Textarea(
                attrs={
                    "placeholder": "What do you want to share?",
                    "rows": 20,
                    "id": "text-input",
                }
            ),
            "projects": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy(
                    "write:project-autocomplete", kwargs={"form_type": "post"}
                ),
                attrs={"data-placeholder": "Type to select projects"},
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super(PostForm, self).__init__(*args, **kwargs)
        self.fields["title"].label = ""
        self.fields["content"].label = ""
        self.fields["comments_enabled"].label = "Enable replies"
        self.fields["comments_enabled"].initial = (
            user.enable_replies_by_default if user else True
        )
        self.fields["projects"].label = ""
        self.fields["projects"].help_text = (
            "Posts in projects appear only on their respective project pages, not in the general post list."
        )
        self.fields["share_to_feed"].label = "Share to feed"
        self.fields["share_to_feed"].initial = (
            user.enable_share_to_feed_by_default if user else False
        )


class SayForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
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
        user = kwargs.pop("user", None)

        super(SayForm, self).__init__(*args, **kwargs)

        self.fields["content"].label = ""
        self.fields["comments_enabled"].label = "Enable replies"
        self.fields["comments_enabled"].initial = (
            user.enable_replies_by_default if user else False
        )


class PinForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = Pin
        fields = [
            "title",
            "url",
            "content",
            "projects",
            "comments_enabled",
            "share_to_feed",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Pin title..."}),
            "url": forms.TextInput(attrs={"placeholder": "https://www.example.com"}),
            "content": forms.Textarea(
                attrs={
                    "placeholder": "What do you want to share?",
                    "id": "text-input",
                }
            ),
            "projects": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy(
                    "write:project-autocomplete", kwargs={"form_type": "pin"}
                ),
                attrs={"data-placeholder": "Type to select projects"},
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super(PinForm, self).__init__(*args, **kwargs)
        self.fields["title"].label = ""
        self.fields["url"].label = ""
        self.fields["content"].label = ""
        self.fields["projects"].label = ""
        self.fields["projects"].help_text = (
            "Pins in projects appear only on their respective project pages, not in the general pin list."
        )
        self.fields["comments_enabled"].label = "Enable replies"
        self.fields["comments_enabled"].initial = (
            user.enable_replies_by_default if user else True
        )
        self.fields["share_to_feed"].label = "Share to feed"
        self.fields["share_to_feed"].initial = (
            user.enable_share_to_feed_by_default if user else False
        )


class CommentForm(forms.ModelForm):
    content = forms.CharField(widget=forms.Textarea(attrs={"id": "text-input"}))

    class Meta(auto_prefetch.Model.Meta):
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
        user = kwargs.pop("user", None)
        super(ActivityFeedSayForm, self).__init__(*args, **kwargs)
        self.fields["comments_enabled"].initial = (
            user.enable_replies_by_default if user else True
        )
        self.fields["comments_enabled"].label = "Enable replies"


class RepostForm(forms.ModelForm):
    content = forms.CharField(widget=forms.Textarea(attrs={"id": "text-input"}))

    class Meta(auto_prefetch.Model.Meta):
        model = Repost
        fields = ["content", "comments_enabled"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super(RepostForm, self).__init__(*args, **kwargs)

        self.fields["content"].label = ""
        self.fields["content"].required = False
        self.fields["comments_enabled"].label = "Enable replies"

        # Check if the user is not None and has the attribute 'enable_replies_by_default'
        if user and hasattr(user, "enable_replies_by_default"):
            self.fields["comments_enabled"].initial = user.enable_replies_by_default
        else:
            self.fields["comments_enabled"].initial = True


class LuvListForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        instance = kwargs.get("instance", None)
        super(LuvListForm, self).__init__(*args, **kwargs)

        # Disable fields if the user is not the creator
        if instance is not None and instance.user != user:
            self.fields["title"].disabled = True
            self.fields["notes"].disabled = True
            self.fields["allow_collaboration"].disabled = True

        self.fields["order_preference"].required = False
        self.fields["order_preference"].label = "Display Order"
        self.fields["order_preference"].help_text = (
            "e.g. Ascending = 1, 2, 3...; Descending = 3, 2, 1..."
        )
        self.fields["source"].help_text = "e.g. URL to the source of the list."
        self.fields["allow_collaboration"].help_text = (
            "Allow others to add items to the list."
        )

    class Meta(auto_prefetch.Model.Meta):
        model = LuvList
        fields = [
            "title",
            "short_name",
            "notes",
            "source",
            "wikipedia",
            "order_preference",
            "allow_collaboration",
            "items_per_page",
        ]
        help_texts = {
            "items_per_page": "How many items to show per page. Leave blank to show all.",
            "short_name": "A short name for adding the surprise page to the home screen.",
        }


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

    class Meta(auto_prefetch.Model.Meta):
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


class CustomContentInListFormSet(forms.models.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        # Optionally receive a pre-filtered queryset that should not be re-filtered
        qs = kwargs.pop("queryset", None)
        super(CustomContentInListFormSet, self).__init__(*args, **kwargs)
        if qs is not None:
            self.queryset = qs


ContentInListFormSet = forms.inlineformset_factory(
    LuvList,
    ContentInList,
    form=ContentInListForm,
    formset=CustomContentInListFormSet,
    extra=1,
    can_delete=True,
    widgets={
        "content_url": forms.URLInput(attrs={"required": False}),
        "order": forms.NumberInput(attrs={"required": False}),
    },
)


class AlbumForm(forms.ModelForm):
    class Meta:
        model = Album
        fields = ["name", "notes", "comments_enabled"]


class PhotoUploadForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ["photo"]


class PhotoForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ["photo", "notes", "comments_enabled"]


class PhotoNotesForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ["notes"]
        widgets = {
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Write something about this photo?",
                }
            ),
        }
