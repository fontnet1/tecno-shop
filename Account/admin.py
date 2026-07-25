from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .forms import UserCreationForm, UserChangeForm
from Account.models import User, AddAddress


class UserAdmin(BaseUserAdmin):
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm

    # The fields to be used in displaying the User model.
    list_display = ["email", "phone", "full_name", "is_admin", "is_active"]
    list_filter = ["is_admin"]
    fieldsets = [
        (None, {"fields": ["phone", "password"]}),
        ("Personal Information", {"fields": ["full_name", "email"]}),
        ("Permissions", {"fields": ["is_admin", "is_active"]}),
    ]
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["phone", "full_name", "password1", "password2"],
            },
        ),
    ]
    search_fields = ["phone", "full_name"]
    ordering = ["phone"]
    filter_horizontal = []


# Now register the new UserAdmin...
admin.site.register(User, UserAdmin)
# OTP should not be registered in admin panel — contains sensitive codes
admin.site.register(AddAddress)