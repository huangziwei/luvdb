from django import forms

from .models import AltProfile, AltProfileTemplate


class AltProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["custom_html"].required = False
        self.fields["custom_css"].required = False

    class Meta:
        model = AltProfile
        fields = ["custom_html", "custom_css"]


class ApplyTemplateForm(forms.Form):
    template_id = forms.IntegerField(widget=forms.HiddenInput())
