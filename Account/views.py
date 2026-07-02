from django.shortcuts import render,redirect
from django.views import View
from .forms import LoginForm
from  django.contrib.auth import authenticate, login, logout

"""def user_login(request):
    return render(request,  "account/login.html")
"""


class Login(View):

    def get(self, request):
        form = LoginForm()

        if request.user.is_authenticated:
            return redirect("/")

        return render(
            request,
            "account/login.html",
            {"form": form},
        )

    def post(self, request):
        form = LoginForm(request.POST)

        if form.is_valid():
            login(request, form.user)
            return redirect("/")   # یا نام URL خودت

        return render(
            request,
            "account/login.html",
            {"form": form},
        )