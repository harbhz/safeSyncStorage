from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile, UploadFile

class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', )

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('gender', 'mobile', 'address', 'pin', 'city', 'state')

class FileUploadForm(forms.ModelForm):
    file_name = forms.CharField(max_length=100, required=True)
    file_password = forms.CharField(
        max_length=16, min_length=16, required=True,
        help_text="File Password Must be 16 Characters Long."
    )
    file_path = forms.FileField(required=True)
    class Meta:
        model = UploadFile
        fields = ('file_name', 'file_password', 'file_path')
