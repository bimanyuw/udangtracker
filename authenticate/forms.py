from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields # + ('email',) # Contoh tambah field email

class CustomAuthenticationForm(AuthenticationForm):

    pass