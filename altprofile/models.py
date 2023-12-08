from django.conf import settings
from django.db import models


class AltProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    custom_html = models.TextField(blank=True)
    custom_css = models.TextField(blank=True)


class AltProfileTemplate(models.Model):
    name = models.CharField(max_length=100)
    html_content = models.TextField(blank=True)
    css_content = models.TextField(blank=True)

    def __str__(self):
        return self.name
