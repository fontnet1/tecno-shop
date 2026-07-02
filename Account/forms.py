from Account.models import User
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import ValidationError
from django import forms
from django import forms
from django.contrib.auth import authenticate




class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""

    password1 = forms.CharField(label="کذرواژه", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="گذرواژه را دوباره وارد کنید", widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ["phone",]

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    disabled password hash display field.
    """

    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ["email","phone", "password", "is_active", "is_admin"]


class LoginForm(forms.Form):
    phone = forms.CharField(
        max_length=11,
        widget=forms.TextInput(
            attrs={
                "id": "login-phone",
                "class": "form-control",
                "placeholder": "09xxxxxxxxx",
            }
        ),
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "id": "login-password",
                "class": "form-control",
                "placeholder": "Enter your password",
            }
        )
    )

    def clean(self):
        cleaned_data = super().clean()

        phone = cleaned_data.get("phone")
        password = cleaned_data.get("password")

        if phone and password:
            user = authenticate(
                username=phone,
                password=password,
            )

            if user is None:
                raise forms.ValidationError(
                    "Phone number or password is incorrect."
                )

            self.user = user

        return cleaned_data