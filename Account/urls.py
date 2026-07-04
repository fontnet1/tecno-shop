from django.urls import path
from django.views.generic import TemplateView

from . import  views
app_name = "Account"
urlpatterns = [
    path('login/', views.Login.as_view(), name='login'),
    path('resester/', views.Register.as_view(), name='resester'),
    path("otp/", views.VerifyOTP.as_view(), name='otp'),
    path("otp/resend/", views.ResendOTP.as_view(), name="resend_otp"),
]