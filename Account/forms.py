from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinLengthValidator


User = get_user_model()


# ─── Validators ────────────────────────────────────────────────────
IRANIAN_PHONE_VALIDATOR = RegexValidator(
    regex=r"^09\d{9}$",
    message="Phone number must start with 09 and be 11 digits.",
    code="invalid_phone",
)

PASSWORD_VALIDATORS = [
    MinLengthValidator(8, message="Password must be at least 8 characters long."),
    RegexValidator(
        regex=r"[A-Z]",
        message="Password must contain at least one uppercase letter.",
        code="no_uppercase",
    ),
    RegexValidator(
        regex=r"[a-z]",
        message="Password must contain at least one lowercase letter.",
        code="no_lowercase",
    ),
    RegexValidator(
        regex=r"\d",
        message="Password must contain at least one digit.",
        code="no_digit",
    ),
]


# ─── Admin Forms ──────────────────────────────────────────────────
class UserCreationForm(forms.ModelForm):
    """User creation form for admin panel"""

    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = ["phone"]

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """User edit form for admin panel"""

    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ["email", "phone", "password", "is_active", "is_admin"]


# ─── Auth Forms ────────────────────────────────────────────────────
class LoginForm(forms.Form):
    phone = forms.CharField(
        max_length=11,
        validators=[IRANIAN_PHONE_VALIDATOR],
        widget=forms.TextInput(
            attrs={
                "id": "login-phone",
                "class": "form-control",
                "placeholder": "09xxxxxxxxx",
                "inputmode": "numeric",
                "autocomplete": "tel",
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
        validators=[IRANIAN_PHONE_VALIDATOR],
        widget=forms.TextInput(
            attrs={
                "id": "reg-phone",
                "placeholder": "09xxxxxxxxx",
                "inputmode": "numeric",
                "autocomplete": "tel",
            }
        ),
    )

    password = forms.CharField(
        validators=PASSWORD_VALIDATORS,
        widget=forms.PasswordInput(
            attrs={
                "id": "reg-password",
                "placeholder": "Minimum 8 characters, including uppercase, lowercase, and digit",
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
            raise forms.ValidationError("This phone number is already registered.")

        return phone

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if email:
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError("This email is already registered.")

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
            raise forms.ValidationError("Invalid verification code.")

        return otp


class LoginOTPForm(forms.Form):
    phone = forms.CharField(
        max_length=11,
        validators=[IRANIAN_PHONE_VALIDATOR],
        widget=forms.TextInput(
            attrs={
                "id": "login-phone",
                "placeholder": "09xxxxxxxxx",
                "inputmode": "numeric",
                "autocomplete": "tel",
            }
        ),
    )

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        # Do not reveal whether user exists or not
        return phone


class ResetPasswordForm(forms.Form):
    password = forms.CharField(
        validators=PASSWORD_VALIDATORS,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Minimum 8 characters, including uppercase, lowercase, and digit",
            }
        ),
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Re-enter your password",
            }
        ),
    )

    def clean(self):
        cleaned = super().clean()

        if cleaned.get("password") and cleaned.get("confirm_password"):
            if cleaned["password"] != cleaned["confirm_password"]:
                raise forms.ValidationError("Passwords do not match.")

        return cleaned


class ForgotPasswordForm(forms.Form):
    phone = forms.CharField(
        max_length=11,
        validators=[IRANIAN_PHONE_VALIDATOR],
        widget=forms.TextInput(
            attrs={
                "id": "phone",
                "placeholder": "09xxxxxxxxx",
                "inputmode": "numeric",
                "autocomplete": "tel",
            }
        ),
    )

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        # Do not reveal whether user exists or not
        return phone