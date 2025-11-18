from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.contrib import messages


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Akun berhasil dibuat! Silakan masuk.')
            
            # Alihkan ke halaman login
            return redirect('authenticate:login') 
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'register.html', {'auth_form': form, 'page_title': 'Registrasi Pengguna Baru'})

# View Login
def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('dashboard')
    else:
        form = CustomAuthenticationForm()

    return render(request, 'login.html', {'auth_form': form, 'page_title': 'Login Udang Tracker'})

# View Logout
def logout_view(request):
    auth_logout(request)
    return redirect('login')