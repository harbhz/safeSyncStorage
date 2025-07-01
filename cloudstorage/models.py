from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

GENDER_CHOICES = (
    ('Male', 'Male'),
    ('Female', 'Female'),
)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mobile = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=200, blank=True, null=True)
    state = models.CharField(max_length=200, blank=True, null=True)
    pin = models.CharField(max_length=10, blank=True, null=True)
    country = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class Contact(models.Model):
    name = models.CharField(max_length=150)
    email = models.CharField(max_length=150)
    mobile = models.CharField(max_length=30)
    description = models.TextField(max_length=1050)
    status = models.PositiveSmallIntegerField(default=1)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.email})"

class UploadFile(models.Model):
    file_name = models.CharField(max_length=255)
    file_password = models.CharField(max_length=100, null=True, blank=True)
    file_path = models.FileField(upload_to='upload/', verbose_name="Upload File", null=True, blank=True)
    encrypted_data = models.BinaryField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    status = models.PositiveSmallIntegerField(default=1)
    file_name_with_ext = models.CharField(max_length=255, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.file_name

class ActivityLogs(models.Model):
    ACTIVITY_LOGS = (
        ('Login', 'Login'),
        ('Logout', 'Logout'),
        ('FileUpload', 'FileUpload'),
        ('DeleteFile', 'DeleteFile'),
        ('FileTransfer', 'FileTransfer'),
        ('UpdateProfile', 'UpdateProfile'),
        ('ChangePassword', 'ChangePassword'),
        ('SendChat', 'SendChat'),
        ('DeleteChat', 'DeleteChat'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_log_user")
    activity_log = models.CharField(max_length=50, choices=ACTIVITY_LOGS)
    ip_address = models.CharField(max_length=50, null=True, blank=True)
    user_agent = models.CharField(max_length=500, null=True, blank=True)
    description = models.TextField(max_length=1000, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.activity_log}"

class FileTransfer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="file_sender_user")
    file_name = models.ForeignKey(UploadFile, on_delete=models.CASCADE)
    remarks = models.CharField(max_length=250)
    receiver_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="file_receiver_user")
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} to {self.receiver_user.username}"

class Chat(models.Model):
    sender_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_sender_user")
    message = models.CharField(max_length=250)
    receiver_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_receiver_user")
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender_user.username} to {self.receiver_user.username}"
