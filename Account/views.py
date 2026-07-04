from Account.models import OTP
from .forms import LoginForm,VerifyOTPForm,RegisterForm
from  django.contrib.auth import login, logout
from django.shortcuts import render, redirect
from django.views import View
import ghasedak_sms
from tecno_shop import settings
from  random import randint
from .models import User
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from random import randint
from datetime import timedelta
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.contrib import messages

#my api
sms_api = ghasedak_sms.Ghasedak(settings.GHASEDAK_API_KEY)



#seting progect
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

        if form.is_valid():
            cd=form.cleaned_data
            randcode=randint(100000,999999)
            newotpcommand = ghasedak_sms.SendOtpInput(
                send_date=None,
                receptors=[
                    ghasedak_sms.SendOtpReceptorDto(
                        mobile=cd["phone"],
                    )
                ],
                template_name='Ghasedak',
                inputs=[
                    ghasedak_sms.SendOtpInput.OtpInput(param='Code', value=f'{randcode}'),
                ],
                udh=False

            )
            with transaction.atomic():
                OTP.objects.filter(phone=cd["phone"]).delete()
                OTP.objects.create(
                    phone=cd["phone"],
                    code=randcode,
                )
                User.objects.create_user(
                    phone=cd["phone"],
                    email=cd["email"],
                    full_name=cd["full_name"],
                    password=cd["password"],
                    is_active=False,
                )
            request.session["phone"] = cd["phone"]
            print(newotpcommand)
            return redirect("Account:otp")

        return render(
            request,
            "account/register.html",
            {
                "form": form,
            },
        )




class VerifyOTP(View):

    def dispatch(self, request, *args, **kwargs):

        if request.user.is_authenticated:
            return redirect("home")

        if "phone" not in request.session:
            return redirect("Account:resester")

        return super().dispatch(request, *args, **kwargs)

    def get(self, request):



        form = VerifyOTPForm()
        phone = request.session.get("phone")
        otp = OTP.objects.filter(phone=phone).first()
        expire_timestamp = int(
            (otp.created_at + timedelta(minutes=2)).timestamp()
        )
        masked_phone = f"{phone[:4]}***{phone[-2:]}"
        return render(
            request,
            "Account/otp.html",
            {
                "form": form,
                "phone": masked_phone,
                "expire_timestamp":expire_timestamp
            },
        )

    def post(self, request):

        form = VerifyOTPForm(request.POST)
        print(form)
        if form.is_valid():

            otp = form.cleaned_data["otp"]

            phone = request.session.get("phone")

            otp_object = OTP.objects.filter(
                phone=phone,
                code=otp,
                created_at__gte=timezone.now() - timedelta(minutes=OTP_EXPIRE_MINUTES)

            ).first()
            print("dorost")

            if otp_object is None:
                form.add_error(None, "Invalid verification code.")

                return render(
                    request,
                    "Account/otp.html",
                    {"form": form},
                )
            user = User.objects.filter(phone=phone).first()
            if user is None:
                form.add_error(None, "User not found.")
                return render(
                    request,
                    "Account/otp.html",
                    {"form": form},
                )
            user.is_active = True
            user.save()

            login(request, user)
            request.session.pop("phone", None)
            otp_object.delete()

            return redirect("home:home")
        print("form kar nemikone")
        return render(
            request,
            "Account/otp.html",
            {"form": form},
        )
class ResendOTP(View):

    def post(self, request):

        phone = request.session.get("phone")

        if phone is None:
            return redirect("Account:resester")

        otp = OTP.objects.filter(phone=phone).first()

        # جلوگیری از ارسال پشت سر هم
        if otp and otp.created_at > timezone.now() - timedelta(seconds=60):
            messages.error(request, "Please wait 60 seconds before requesting a new code.")
            return redirect("Account:otp")

        OTP.objects.filter(phone=phone).delete()

        code = randint(100000, 999999)

        OTP.objects.create(
            phone=phone,
            code=code,
        )

        newotpcommand = ghasedak_sms.SendOtpInput(
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

        # TODO:
        # ارسال پیامک با SDK قاصدک

        messages.success(request, "A new verification code has been sent.")

        return redirect("Account:otp")