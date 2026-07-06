from os import name

from Account.models import OTP
from .forms import LoginForm,VerifyOTPForm,RegisterForm,LoginOTPForm,ResetPasswordForm,ForgotPasswordForm
from  django.contrib.auth import login, logout
from django.shortcuts import render, redirect
import ghasedak_sms
from tecno_shop import settings
from .models import User
from django.db import transaction
from datetime import timedelta
from django.utils import timezone
from django.views import View
from random import randint

#my api
sms_api = ghasedak_sms.Ghasedak(settings.GHASEDAK_API_KEY)

def send_otp(phone, purpose):
    """
    ساخت، ذخیره و ارسال کد تایید
    """

    code = randint(100000, 999999)

    OTP.objects.filter(
        phone=phone,
        purpose=purpose,
    ).delete()

    otp = OTP.objects.create(
        phone=phone,
        code=code,
        purpose=purpose,
    )

    sms = ghasedak_sms.SendOtpInput(
        send_date=None,
        receptors=[
            ghasedak_sms.SendOtpReceptorDto(
                mobile=phone,
            )
        ],
        template_name="Ghasedak",
        inputs=[
            ghasedak_sms.SendOtpInput.OtpInput(
                param="Code",
                value=str(code),
            ),
        ],
        udh=False,
    )

    # بعداً اینجا فقط ارسال واقعی را انجام می‌دهی
    # sms_api.send_otp(sms)

    print(sms)

    return otp


#seting project
OTP_EXPIRE_MINUTES=2
class Login(View):

    def get(self, request):
        form = LoginForm()

        if request.user.is_authenticated:
            return redirect("home:home")

        return render(
            request,
            "account/login.html",
            {"form": form},
        )

    def post(self, request):
        form = LoginForm(request.POST)

        if form.is_valid():
            login(request, form.user)
            return redirect("home:home")   # یا نام URL خودت

        return render(
            request,
            "account/login.html",
            {"form": form},
        )


class Register(View):

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home:home")

        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = RegisterForm()

        return render(
            request,
            "account/register.html",
            {
                "form": form,
            },
        )

    def post(self, request):
        form = RegisterForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                "account/register.html",
                {
                    "form": form,
                },
            )

        cd = form.cleaned_data

        with transaction.atomic():

            User.objects.create_user(
                phone=cd["phone"],
                email=cd["email"],
                full_name=cd["full_name"],
                password=cd["password"],
                is_active=False,
            )

            send_otp(
                phone=cd["phone"],
                purpose=OTP.REGISTER,
            )

        request.session["phone"] = cd["phone"]
        request.session["purpose"] = OTP.REGISTER

        return redirect("Account:otp")


class VerifyOTP(View):

    def dispatch(self, request, *args, **kwargs):

        if request.user.is_authenticated:
            return redirect("home:home")

        if "phone" not in request.session:
            return redirect("Account:resester")

        if "purpose" not in request.session:
            return redirect("Account:resester")

        return super().dispatch(request, *args, **kwargs)

    def get(self, request):

        phone = request.session["phone"]
        purpose = request.session["purpose"]

        otp = OTP.objects.filter(
            phone=phone,
            purpose=purpose,
        ).first()

        if otp is None:
            return redirect("Account:resester")

        form = VerifyOTPForm()

        expire_timestamp = int(
            (
                otp.created_at +
                timedelta(minutes=OTP_EXPIRE_MINUTES)
            ).timestamp()
        )

        masked_phone = f"{phone[:4]}***{phone[-2:]}"

        return self.render_otp(request, form)

    def render_otp(self, request, form):
        phone = request.session["phone"]
        purpose = request.session["purpose"]

        otp = OTP.objects.filter(
            phone=phone,
            purpose=purpose,
        ).first()

        expire_timestamp = int(
            (
                    otp.created_at +
                    timedelta(minutes=OTP_EXPIRE_MINUTES)
            ).timestamp()
        )

        masked_phone = f"{phone[:4]}***{phone[-2:]}"

        return render(
            request,
            "Account/otp.html",
            {
                "form": form,
                "phone": masked_phone,
                "expire_timestamp": expire_timestamp,
            },
        )

    def post(self, request):

        form = VerifyOTPForm(request.POST)

        if not form.is_valid():
            return self.render_otp(request, form)

        otp = form.cleaned_data["otp"]

        phone = request.session.get("phone")
        purpose = request.session.get("purpose")

        otp_object = OTP.objects.filter(
            phone=phone,
            code=otp,
            purpose=purpose,
            created_at__gte=timezone.now() - timedelta(minutes=OTP_EXPIRE_MINUTES),
        ).first()

        if otp_object is None:
            form.add_error(None, "Invalid verification code.")
            return self.render_otp(request, form)

        user = User.objects.filter(phone=phone).first()

        if user is None:
            form.add_error(None, "User not found.")
            return self.render_otp(request, form)

        # ==========================
        # ثبت نام
        # ==========================
        if purpose == OTP.REGISTER:
            user.is_active = True
            user.save()
            login(request, user)

        # ==========================
        # ورود با کد
        # ==========================
        elif purpose == OTP.LOGIN:

            if not user.is_active:
                form.add_error(None, "Your account is inactive.")
                return render(
                    request,
                    "Account/otp.html",
                    {"form": form},
                )

            login(request, user)

        # ==========================
        # فراموشی رمز
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

class ResendOTP(View):

    def post(self, request):

        phone = request.session.get("phone")
        purpose = request.session.get("purpose")

        if not phone or not purpose:
            return redirect("Account:register")

        send_otp(
            phone=phone,
            purpose=purpose,
        )

        return redirect("Account:otp")

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

        send_otp(
            phone=phone,
            purpose=OTP.LOGIN,
        )

        request.session["phone"] = phone
        request.session["purpose"] = OTP.LOGIN

        return redirect("Account:otp")

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
            {
                "form": form,
            },
        )

    def post(self, request):

        form = ResetPasswordForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                "Account/reset_password.html",
                {
                    "form": form,
                },
            )

        user = User.objects.get(
            id=request.session["reset_password_user"]
        )

        user.set_password(
            form.cleaned_data["password"]
        )

        user.save()

        request.session.pop("reset_password_user", None)

        login(request, user)

        return redirect("home:home")

class ForgotPassword(View):

    def get(self, request):

        form = LoginOTPForm()

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
                "Account/login_with_otp_AND_forgot_password.html.",
                {
                    "form": form,
                    "nameform":"Forgot Password",

                },
            )

        phone = form.cleaned_data["phone"]

        send_otp(
            phone=phone,
            purpose=OTP.RESET_PASSWORD,
        )

        request.session["phone"] = phone
        request.session["purpose"] = OTP.RESET_PASSWORD

        return redirect("Account:otp")

class Choose_a_password_or_code(View):
    def get(self, request):

        return render(
            request,
            "Account/Choose_a_password_or_code.html",
            {
                "nameform": "Forgot Password",
            },
        )