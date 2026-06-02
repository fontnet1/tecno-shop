from django.urls import path
from . import  views
from home.views import HomePageView
app_name = "home"
urlpatterns = [
    path('',views.HomePageView.as_view(), name='home'),

]