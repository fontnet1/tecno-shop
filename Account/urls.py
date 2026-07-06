from django.urls import path
from django.views.generic import TemplateView

from . import  views
app_name = "Account"
urlpatterns = [
    path('login/', views.Login.as_view(), name='login'),
    path('resester/', views.Register.as_view(), name='resester'),
    path("otp/", views.VerifyOTP.as_view(), name='otp'),
    path("otp/resend/", views.ResendOTP.as_view(), name="resend_otp"),
    path("login-with-otp/",views.LoginWithOTP.as_view(),name="login_with_otp"),
    path("forgot-password/",views.ForgotPassword.as_view(),name="forgot_password"),
    path("reset-password/",views.ResetPassword.as_view(),name="reset_password"),
    path("choose_a_password_or_code/",views.Choose_a_password_or_code.as_view(),name="choose_a_password_or_code"),
]