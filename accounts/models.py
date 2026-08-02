import os
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.deconstruct import deconstructible

from .managers import UserManager


@deconstructible
class PrivateResumeStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(location=settings.PRIVATE_MEDIA_ROOT, base_url=None)

    def url(self, name):
        raise ValueError("Resume files are private and do not have public URLs.")


resume_storage = PrivateResumeStorage()


def resume_upload_path(instance, filename):
    extension = os.path.splitext(filename)[1].lower()
    return f"resumes/user_{instance.pk or 'new'}/{uuid.uuid4().hex}{extension}"


def validate_resume_size(upload):
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError("Resume must be 5 MB or smaller.")


class User(AbstractUser):
    class Role(models.TextChoices):
        JOB_SEEKER = "seeker", "Job seeker"
        EMPLOYER = "employer", "Employer"

    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=120)
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.JOB_SEEKER)
    preferred_language = models.CharField(max_length=2, choices=(("kn", "ಕನ್ನಡ"), ("en", "English")), default="kn")
    resume = models.FileField(
        upload_to=resume_upload_path,
        storage=resume_storage,
        validators=[FileExtensionValidator(["pdf", "doc", "docx"]), validate_resume_size],
        blank=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]
    objects = UserManager()

    def __str__(self):
        return f"{self.full_name} ({self.email})"


class OTPChallenge(models.Model):
    email = models.EmailField(db_index=True)
    code_hash = models.CharField(max_length=128)
    purpose = models.CharField(max_length=20, default="login")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_valid(self):
        return self.consumed_at is None and self.expires_at > timezone.now() and self.attempts < 5

    @classmethod
    def recent_count(cls, email):
        return cls.objects.filter(email=email, created_at__gte=timezone.now() - timedelta(minutes=10)).count()
