from django.urls import path

from .views import (
    PersonAutoComplete,
    PersonCreateView,
    PersonDetailView,
    PersonUpdateView,
    RoleAutocomplete,
    RoleCreateView,
)

app_name = "entity"

urlpatterns = [
    # person
    path("person/create/", PersonCreateView.as_view(), name="person_create"),
    path("person/<int:pk>/", PersonDetailView.as_view(), name="person_detail"),
    path("person/<int:pk>/update/", PersonUpdateView.as_view(), name="person_update"),
    path(
        "person-autocomplete/", PersonAutoComplete.as_view(), name="person-autocomplete"
    ),
    # role
    path("role/create/", RoleCreateView.as_view(), name="role_create"),
    path("role-autocomplete/", RoleAutocomplete.as_view(), name="role-autocomplete"),
]
