import os
from os.path import basename
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.edit import DeleteView, CreateView
from django.views.generic import ListView, TemplateView
from django.db import transaction

from .models import (
    Contact,
    UploadFile,
    ActivityLogs,
    FileTransfer,
    Chat
)
from .forms import SignUpForm, ProfileForm, UserForm, FileUploadForm

# Encryption imports
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Home page view
def home(request):
    return render(request, 'index.html')

# Utility: Activity log
def activity_log_function(user, activity, event_request, description=None):
    ip_address = event_request.META.get('REMOTE_ADDR', '')
    user_agent = event_request.META.get('HTTP_USER_AGENT', '')
    ActivityLogs.objects.create(
        user=user,
        activity_log=activity,
        ip_address=ip_address,
        user_agent=user_agent,
        description=description
    )

# User registration
def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'register.html', {'form': form})

# Password change
@login_required(login_url='/login/')
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            activity_log_function(
                user=request.user,
                activity="ChangePassword",
                event_request=request
            )
            return redirect('account/change_password')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'account/change_password.html', {'form': form})

# Contact form
class ContactView(CreateView):
    model = Contact
    fields = ['name','email','mobile','description']
    template_name = 'contact.html'
    success_url = '/thanks/'

# File listing for the logged-in user
class FileListView(ListView):
    model = UploadFile
    paginate_by = 20

    def get_queryset(self):
        return UploadFile.objects.filter(user=self.request.user)

# File upload with AES encryption
class UploadCreate(CreateView):
    model = UploadFile
    form_class = FileUploadForm
    template_name = 'cloudstorage/addfile.html'
    success_url = '/thanks/'

    def form_valid(self, form):
        form.instance.user = self.request.user
        file_password = form.cleaned_data['file_password']
        file_key = bytes(file_password, 'utf-8')
        file_name = basename(form.cleaned_data['file_path'].name)
        file_data = form.cleaned_data['file_path'].read()
        encrypted_data = self.encrypt_file(file_data, file_key)
        form.instance.encrypted_data = encrypted_data
        form.instance.file_name_with_ext = file_name
        activity_log_function(
            user=self.request.user,
            activity="FileUpload",
            event_request=self.request
        )
        return super().form_valid(form)

    def pad(self, data):
        padder = padding.PKCS7(128).padder()
        return padder.update(data) + padder.finalize()

    def encrypt_file(self, data, key):
        data = self.pad(data)
        cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
        encryptor = cipher.encryptor()
        return encryptor.update(data) + encryptor.finalize()

# File delete view
class FileDelete(DeleteView):
    model = UploadFile
    success_url = '/filelist/'

    def form_valid(self, form):
        messages.success(self.request, "The file was deleted successfully.")
        activity_log_function(
            user=self.request.user,
            activity="DeleteFile",
            event_request=self.request
        )
        return super().form_valid(form)

# File download with decryption
class DownloadFile(TemplateView):
    template_name = 'cloudstorage/download_file_form.html'

    def post(self, request, *args, **kwargs):
        file_password = request.POST.get('file_password')
        file_id = kwargs.get('pk')
        upload_file = get_object_or_404(UploadFile, id=file_id, user=request.user)

        if file_password and len(file_password) == 16:
            encrypted_file_content = upload_file.encrypted_data
            key = file_password.encode('utf-8')
            backend = default_backend()
            cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=backend)
            decryptor = cipher.decryptor()
            decrypted_file_content = decryptor.update(encrypted_file_content) + decryptor.finalize()

            # Remove PKCS7 padding
            unpadder = padding.PKCS7(128).unpadder()
            try:
                decrypted_file_content = unpadder.update(decrypted_file_content) + unpadder.finalize()
            except ValueError:
                return render(request, self.template_name, {
                    'errors': "Invalid decryption key or corrupted file."
                })

            response = HttpResponse(decrypted_file_content, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{upload_file.file_name_with_ext}"'
            return response
        else:
            return render(request, self.template_name, {
                'errors': "Please provide a valid 16-character password."
            })

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

# Profile update view
@login_required
@transaction.atomic
def update_profile(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            activity_log_function(
                user=request.user,
                activity="UpdateProfile",
                event_request=request
            )
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = ProfileForm(instance=request.user.profile)
    return render(request, 'account/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

# Activity log listing
class ActivityLogListView(ListView):
    model = ActivityLogs
    paginate_by = 50

    def get_queryset(self):
        return ActivityLogs.objects.filter(user=self.request.user).order_by('-id')

# File transfer listing
class TransferListView(ListView):
    model = FileTransfer
    paginate_by = 50

    def get_queryset(self):
        return FileTransfer.objects.filter(Q(user=self.request.user) | Q(receiver_user=self.request.user))

# File transfer creation
class TransferFileCreate(TemplateView):
    template_name = 'cloudstorage/transferfile.html'
    success_url = '/thanks/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        file_list = UploadFile.objects.filter(user=self.request.user)
        context['file_list'] = file_list
        return context

    def post(self, request, *args, **kwargs):
        receiver_id = request.POST.get('receiver_id')
        file_id = request.POST.get('file_id')
        remarks = request.POST.get('remarks')
        sender_user = self.request.user
        if receiver_id and sender_user and file_id:
            file_data = FileTransfer.objects.create(
                user=sender_user,
                file_name_id=file_id,
                receiver_user_id=receiver_id,
                remarks=remarks
            )
            activity_log_function(
                user=self.request.user,
                activity="FileTransfer",
                event_request=self.request
            )
            if file_
                return redirect('filetransfer-list')
        context = self.get_context_data(**kwargs)
        context['errors'] = "Invalid transfer data."
        return self.render_to_response(context)

# Chat creation and listing
class ChatCreateListView(CreateView, ListView):
    model = Chat
    template_name = 'cloudstorage/chat_list.html'
    fields = ('receiver_user', 'message')
    success_url = reverse_lazy('chat')

    def form_valid(self, form):
        form.instance.sender_user = self.request.user
        activity_log_function(
            user=self.request.user,
            activity="SendChat",
            event_request=self.request,
            description=form.instance.message
        )
        return super().form_valid(form)

    def get_queryset(self):
        current_user = self.request.user
        return Chat.objects.filter(Q(sender_user=current_user) | Q(receiver_user=current_user))

# Chat deletion
@login_required
def delete_chat(request):
    chat_id = request.GET.get('id', None)
    chats = Chat.objects.filter(id=chat_id, sender_user=request.user)
    if chats.exists():
        delete_message = chats.first().message
        chats.delete()
        activity_log_function(
            user=request.user,
            activity="DeleteChat",
            event_request=request,
            description=delete_message
        )
    return redirect('chat')
