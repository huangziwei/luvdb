from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views import View
from django.views.generic import CreateView, DetailView, UpdateView

from .forms import CustomUserCreationForm
from .models import InvitationCode

User = get_user_model()


@login_required
def redirect_to_profile(request):
    return redirect("accounts:detail", username=request.user.username)


class SignUpView(CreateView):
    """View for user signup."""

    form_class = CustomUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        self.object = form.save()
        # set invitation code as used
        if self.object.code_used:  # Check if the user used a code
            self.object.code_used.is_used = True
            self.object.code_used.save()

        return super().form_valid(form)


class AccountDetailView(LoginRequiredMixin, DetailView):
    """Detail view for user accounts."""

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"
    template_name = "accounts/account_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if the user has already generated an invitation code this month
        start_date = datetime.now().replace(day=1)
        code_this_month = self.request.user.codes_generated.filter(
            generated_at__gte=start_date
        ).first()
        # Check if the code is used
        if code_this_month:
            context["can_generate_code"] = False if code_this_month.is_used else True
        return context


class AccountUpdateView(LoginRequiredMixin, UpdateView):
    """Update view for user accounts."""

    model = User
    fields = [
        "display_name",  # Add display_name to the list of fields
        "username",
        "bio",
    ]
    template_name = "accounts/account_update.html"
    slug_field = "username"
    slug_url_kwarg = "username"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user


class GenerateInvitationCodeView(View):
    def post(self, request):
        user = request.user
        # Check if there is an unused code generated by the user
        unused_code = user.codes_generated.filter(is_used=False).first()
        if unused_code:
            code = unused_code
        elif not user.codes_generated.filter(
            generated_at__gte=timezone.now() - timedelta(days=30)
        ).exists():
            # User has not generated a code this month, so generate a new one
            code = InvitationCode.objects.create(generated_by=user)
        else:
            # User has already generated a code this month
            messages.error(
                request, "You can only generate one invitation code per month."
            )
            return redirect("accounts:profile")
        messages.success(
            request,
            mark_safe(
                f'Send this invitation code to your friend: <strong style="color:blue;">{code.code}</strong>.'
            ),
        )
        messages.success(request, "Every invitation code can only be used once. ")
        messages.success(request, "You can only invite one friend every month. ")
        return redirect("accounts:profile")
