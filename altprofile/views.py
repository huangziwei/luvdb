from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect
from django.template import Context, Template
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.generic import DetailView, TemplateView, UpdateView, View

from write.models import Pin, Post, Say

from .forms import AltProfileForm
from .models import AltProfile, AltProfileTemplate

User = get_user_model()


class AltProfileLoginView(LoginView):
    template_name = "altprofile/altprofile_login.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if the user is already logged in
        if request.user.is_authenticated:
            # Redirect to the alternative profile detail page
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        user = self.request.user
        try:
            custom_user = User.objects.get(username=user.username)
            if custom_user.custom_domain:
                # Include the port number for local development
                if settings.HTTP_HOST == "localhost":
                    port = self.request.get_port()
                    if port and port != "80":
                        return f"http://{custom_user.custom_domain}:{port}/"
                else:
                    return f"https://{custom_user.custom_domain}/"
        except User.DoesNotExist:
            pass

        # If no custom domain, use the standard URL structure
        return reverse("altprofile_detail", kwargs={"username": user.username})

    def form_valid(self, form):
        # Perform the standard login procedure
        super().form_valid(form)

        # Redirect to the success URL
        return redirect(self.get_success_url())


class AltProfileDetailView(DetailView):
    """Alternative Detail view for user accounts."""

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"
    template_name = "altprofile/altprofile_detail.html"

    def dispatch(self, request, *args, **kwargs):
        user = get_object_or_404(User, username=self.kwargs["username"])

        if not user.enable_alt_profile:
            return redirect(settings.ROOT_URL + f"/@{user.username}")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["root_url"] = settings.ROOT_URL
        context["me"] = me = self.object
        # context["html"] = self.object.altprofile.custom_html
        # context["css"] = self.object.altprofile.custom_css
        context["posts"] = Post.objects.filter(user=me).order_by("-timestamp")
        context["says"] = Say.objects.filter(user=me).order_by("-timestamp")

        # Render custom_html as a Django template
        custom_html_template = Template(self.object.altprofile.custom_html)
        rendered_html = custom_html_template.render(Context(context))
        context["html"] = mark_safe(rendered_html)  # Mark the rendered HTML as safe
        print(context["html"])
        return context


class AltProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = AltProfile
    form_class = AltProfileForm
    template_name = "altprofile/altprofile_update.html"

    def dispatch(self, request, *args, **kwargs):
        self.login_url = self.get_custom_login_url(request)
        return super().dispatch(request, *args, **kwargs)

    def get_custom_login_url(self, request):
        domain = request.get_host().split(":")[0]
        if settings.HTTP_HOST == "localhost":
            port = request.get_port()
            port_suffix = f":{port}" if port and port != "80" else ""
            custom_login_url = f"http://{domain}{port_suffix}/login/"
        else:
            custom_login_url = f"https://{domain}/login/"
        return custom_login_url

    def get_success_url(self):
        user = self.request.user
        try:
            custom_user = User.objects.get(username=user.username)
            if custom_user.custom_domain:
                # Include the port number for local development
                if settings.HTTP_HOST == "localhost":
                    port = self.request.get_port()
                    if port and port != "80":
                        return f"http://{custom_user.custom_domain}:{port}/"
                else:
                    return f"https://{custom_user.custom_domain}/"
        except User.DoesNotExist:
            pass

        return reverse(
            "altprofile_detail", kwargs={"username": self.request.user.username}
        )

    def get_object(self, queryset=None):
        return AltProfile.objects.get_or_create(user=self.request.user)[0]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["templates"] = AltProfileTemplate.objects.all()

        return context


class ApplyTemplateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        template_id = request.POST.get("template_id")
        template = get_object_or_404(AltProfileTemplate, id=template_id)
        alt_profile, created = AltProfile.objects.get_or_create(user=request.user)
        alt_profile.custom_html = template.html_content
        alt_profile.custom_css = template.css_content
        alt_profile.save()
        return redirect("altprofile_update", username=request.user.username)


class PreviewTemplateView(TemplateView):
    template_name = "altprofile/altprofile_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        template_id = self.kwargs.get("template_id")
        alt_profile_template = get_object_or_404(AltProfileTemplate, id=template_id)
        context["template"] = alt_profile_template
        return context