from django.urls import path
from .views import CustomLoginView, custom_logout_view, toggle_dark_mode, redirect_to_login
from dashboard.views import dashboard_view

urlpatterns = [
    path('', redirect_to_login),  # redirect root to login
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', custom_logout_view, name='logout'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('toggle-theme/', toggle_dark_mode, name='toggle-theme'),
]
