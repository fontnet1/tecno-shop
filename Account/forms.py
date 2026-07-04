from Account.models import User
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django import forms
from django.contrib.auth import get_user_model




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




User = get_user_model()




class RegisterForm(forms.Form):
    full_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "id": "reg-name",
                "placeholder": "Enter your full name",
            }
        ),
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={
                "id": "reg-email",
                "placeholder": "example@email.com",
            }
        ),
    )

    phone = forms.CharField(
        max_length=11,
        widget=forms.TextInput(
            attrs={
                "id": "reg-phone",
                "placeholder": "09xxxxxxxxx",
            }
        ),
    )

    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(
            attrs={
                "id": "reg-password",
                "placeholder": "Minimum 8 characters",
            }
        ),
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "id": "reg-confirm",
                "placeholder": "Re-enter your password",
            }
        ),
    )

    agree = forms.BooleanField(
        widget=forms.CheckboxInput(
            attrs={
                "id": "terms",
            }
        ),
        error_messages={

            "required": "You must accept Terms of Service."
        }
    )

    def clean_phone(self):
        phone = self.cleaned_data["phone"]

        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("This phone number already exists.")

        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if email:
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError("This email already exists.")

        return email

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if password and confirm and password != confirm:
            raise forms.ValidationError(
                "Passwords do not match."
            )

        return cleaned_data

    def save(self):
        user = User.objects.create_user(
            full_name=self.cleaned_data["full_name"],
            email=self.cleaned_data["email"],
            phone=self.cleaned_data["phone"],
            password=self.cleaned_data["password"],
        )

        return user



class VerifyOTPForm(forms.Form):
    otp = forms.CharField(
        min_length=6,
        max_length=6,
        widget=forms.HiddenInput(
            attrs={
                "id": "otp-hidden",
            }
        ),
    )

    def clean_otp(self):
        otp = self.cleaned_data["otp"]

        if not otp.isdigit():
            raise forms.ValidationError("OTP is invalid.")

        return otp