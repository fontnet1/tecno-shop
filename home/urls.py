from django.urls import path
from . import  views
from home.views import HomePageView
from django.views.decorators.cache import cache_page
app_name = "home"
urlpatterns = [
    path('',cache_page(1*1)(views.HomePageView.as_view()), name='home'),

]