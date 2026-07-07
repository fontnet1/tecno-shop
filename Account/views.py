import logging

from Account.models import OTP
from .forms import (
    LoginForm,
    VerifyOTPForm,
    RegisterForm,
    LoginOTPForm,
    ResetPasswordForm,
    ForgotPasswordForm,
)
from django.contrib.auth import login, logout
from django.contrib.messages import success, error, warning
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View
from datetime import timedelta

from .models import User
from .conf import AccountSettings
from .services import OTPService, AuthService

logger = logging.getLogger(__name__)


# ─── Login (Password) ────────────────────────────────────────────
class Login(View):

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("home:home")

        form = LoginForm()
        return render(request, "Account/login.html", {"form": form})

    def post(self, request):
        form = LoginForm(request.POST, request=request)  # ← اینجا

        if form.is_valid():
            login(request, form.user)
            success(request, "Logged in successfully.")
            return redirect("home:home")

        return render(request, "Account/login.html", {"form": form})

# ─── Register ─────────────────────────────────────────────────────
class Register(View):

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home:home")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = RegisterForm()
        return render(
            request,
            "Account/register.html",
            {"form": form},
        )

    def post(self, request):
        form = RegisterForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                "Account/register.html",
                {"form": form},
            )

        cd = form.cleaned_data

        AuthService.register_user(
            phone=cd["phone"],
            full_name=cd["full_name"],
            email=cd.get("email"),
            password=cd["password"],
        )

        OTPService.send_otp(
            phone=cd["phone"],
            purpose=OTP.REGISTER,
        )

        request.session["phone"] = cd["phone"]
        request.session["purpose"] = OTP.REGISTER

        return redirect("Account:otp")


# ─── Verify OTP ───────────────────────────────────────────────────
class VerifyOTP(View):

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home:home")

        if "phone" not in request.session:
            return redirect("Account:register")

        if "purpose" not in request.session:
            return redirect("Account:register")

        return super().dispatch(request, *args, **kwargs)

    def _get_otp_context(self, request):
        """Prepare common context for GET and POST"""
        phone = request.session["phone"]
        purpose = request.session["purpose"]

        otp = OTP.objects.filter(
            phone=phone,
            purpose=purpose,
        ).first()

        if otp is None:
            return None

        expire_timestamp = int(
            (
                otp.created_at +
                timedelta(minutes=AccountSettings.OTP_EXPIRE_MINUTES)
            ).timestamp()
        )

        masked_phone = f"{phone[:4]}***{phone[-2:]}"

        return {
            "phone": masked_phone,
            "expire_timestamp": expire_timestamp,
        }

    def get(self, request):
        context = self._get_otp_context(request)
        if context is None:
            return redirect("Account:register")

        form = VerifyOTPForm()
        context["form"] = form

        return render(
            request,
            "Account/otp.html",
            context,
        )

    def post(self, request):
        form = VerifyOTPForm(request.POST)

        if not form.is_valid():
            context = self._get_otp_context(request)
            if context is None:
                return redirect("Account:register")
            context["form"] = form
            return render(request, "Account/otp.html", context)

        otp_code = form.cleaned_data["otp"]
        phone = request.session.get("phone")
        purpose = request.session.get("purpose")

        # ─── Verify code with Rate Limiting ───
        try:
            otp_object = OTPService.verify_otp(
                phone=phone,
                code=otp_code,
                purpose=purpose,
            )
        except ValueError as e:
            # Attempt rate limit reached
            context = self._get_otp_context(request)
            if context is None:
                return redirect("Account:register")
            form.add_error(None, str(e))
            context["form"] = form
            return render(request, "Account/otp.html", context)

        if otp_object is None:
            context = self._get_otp_context(request)
            if context is None:
                return redirect("Account:register")
            form.add_error(None, "Invalid verification code.")
            context["form"] = form
            return render(request, "Account/otp.html", context)

        user = User.objects.filter(phone=phone).first()

        if user is None:
            context = self._get_otp_context(request)
            if context is None:
                return redirect("Account:register")
            form.add_error(None, "User not found.")
            context["form"] = form
            return render(request, "Account/otp.html", context)

        # ==========================
        # Registration
        # ==========================
        if purpose == OTP.REGISTER:
            user.is_active = True
            user.save()
            login(request, user)
            success(request, "Your account has been activated successfully.")

        # ==========================
        # Login with code
        # ==========================
        elif purpose == OTP.LOGIN:
            if not user.is_active:
                context = self._get_otp_context(request)
                if context is None:
                    return redirect("Account:register")
                form.add_error(None, "Your account is inactive.")
                context["form"] = form
                return render(request, "Account/otp.html", context)

            login(request, user)
            success(request, "Logged in successfully.")

        # ==========================
        # Forgot password
        # ==========================
        elif purpose == OTP.RESET_PASSWORD:
            request.session["reset_password_user"] = user.id
            otp_object.delete()
            request.session.pop("phone", None)
            request.session.pop("purpose", None)
            return redirect("Account:reset_password")

        otp_object.delete()
        request.session.pop("phone", None)
        request.session.pop("purpose", None)

        return redirect("home:home")


# ─── Resend OTP ───────────────────────────────────────────────────
class ResendOTP(View):

    def post(self, request):
        phone = request.session.get("phone")
        purpose = request.session.get("purpose")

        if not phone or not purpose:
            return redirect("Account:register")

        try:
            OTPService.send_otp(phone=phone, purpose=purpose)
        except ValueError as e:
            warning(request, str(e))

        return redirect("Account:otp")


# ─── Login With OTP ───────────────────────────────────────────────
class LoginWithOTP(View):

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home:home")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = LoginOTPForm()
        return render(
            request,
            "Account/login_with_otp_AND_forgot_password.html",
            {
                "form": form,
                "nameform": "Login With Otp",
            },
        )

    def post(self, request):
        form = LoginOTPForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                "Account/login_with_otp_AND_forgot_password.html",
                {
                    "form": form,
                    "nameform": "Login With Otp",
                },
            )

        phone = form.cleaned_data["phone"]
        user = User.objects.filter(phone=phone).first()

        # ─── Do not reveal information: same response ───
        if user and not user.is_active:
            # Inactive user — code is not sent but response is the same
            return render(
                request,
                "Account/login_with_otp_AND_forgot_password.html",
                {
                    "form": form,
                    "nameform": "Login With Otp",
                },
            )

        if user and user.is_active:
            try:
                OTPService.send_otp(phone=phone, purpose=OTP.LOGIN)
                request.session["phone"] = phone
                request.session["purpose"] = OTP.LOGIN
                return redirect("Account:otp")
            except ValueError as e:
                warning(request, str(e))

        # User does not exist — do not reveal
        return render(
            request,
            "Account/login_with_otp_AND_forgot_password.html",
            {
                "form": form,
                "nameform": "Login With Otp",
            },
        )


# ─── Reset Password ───────────────────────────────────────────────
class ResetPassword(View):

    def dispatch(self, request, *args, **kwargs):
        if "reset_password_user" not in request.session:
            return redirect("Account:forgot_password")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = ResetPasswordForm()
        return render(
            request,
            "Account/reset_password.html",
            {"form": form},
        )

    def post(self, request):
        form = ResetPasswordForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                "Account/reset_password.html",
                {"form": form},
            )

        user = User.objects.get(id=request.session["reset_password_user"])

        AuthService.reset_password(
            user_id=user.id,
            new_password=form.cleaned_data["password"],
        )

        request.session.pop("reset_password_user", None)

        success(request, "Password changed successfully. Please log in.")
        return redirect("Account:login")


# ─── Forgot Password ──────────────────────────────────────────────
class ForgotPassword(View):

    def get(self, request):
        form = ForgotPasswordForm()
        return render(
            request,
            "Account/login_with_otp_AND_forgot_password.html",
            {
                "form": form,
                "nameform": "Forgot Password",
            },
        )

    def post(self, request):
        form = ForgotPasswordForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                "Account/login_with_otp_AND_forgot_password.html",
                {
                    "form": form,
                    "nameform": "Forgot Password",
                },
            )

        phone = form.cleaned_data["phone"]
        user = User.objects.filter(phone=phone).first()

        # ─── Do not reveal information ───
        if user:
            try:
                OTPService.send_otp(phone=phone, purpose=OTP.RESET_PASSWORD)
                request.session["phone"] = phone
                request.session["purpose"] = OTP.RESET_PASSWORD
                return redirect("Account:otp")
            except ValueError as e:
                warning(request, str(e))

        # Same response — user cannot tell if number exists or not
        return render(
            request,
            "Account/login_with_otp_AND_forgot_password.html",
            {
                "form": form,
                "nameform": "Forgot Password",
            },
        )


# ─── Logout ───────────────────────────────────────────────────────
class LogoutView(View):

    def post(self, request):
        logout(request)
        success(request, "Logged out successfully.")
        return redirect("Account:login")


# ─── Choose Password or Code ──────────────────────────────────────
class ChoosePasswordOrCode(View):

    def get(self, request):
        return render(
            request,
            "Account/Choose_a_password_or_code.html",
            {
                "nameform": "Forgot Password",
            },
        )