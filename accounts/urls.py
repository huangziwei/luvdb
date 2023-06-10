from django.urls import path

from .views import AccountDetailView, AccountUpdateView, SignUpView, redirect_to_profile

app_name = "accounts"
urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("update/", view=AccountUpdateView.as_view(), name="update"),
    path("<str:username>/", view=AccountDetailView.as_view(), name="detail"),
    path("", view=redirect_to_profile, name="profile"),
]
