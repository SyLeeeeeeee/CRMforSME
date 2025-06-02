from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.http import JsonResponse

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'

def custom_logout_view(request):
    logout(request)
    return redirect('login')

def toggle_dark_mode(request):
    dark_mode = request.session.get('dark_mode', False)
    request.session['dark_mode'] = not dark_mode
    return JsonResponse({'dark_mode': request.session['dark_mode']})

def redirect_to_login(request):
    return redirect('login')
