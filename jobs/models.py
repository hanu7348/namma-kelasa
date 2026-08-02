import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Category(models.Model):
    name_kn = models.CharField(max_length=80)
    name_en = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=8, default="💼")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name_en"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name_en


class EmployerProfile(models.Model):
    class Plan(models.TextChoices):
        FREE = "free", "Free"
        STARTER = "starter", "Starter"
        BUSINESS = "business", "Business"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employer_profile")
    company_name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    gstin = models.CharField(max_length=15, blank=True)
    is_verified = models.BooleanField(default=False)
    plan = models.CharField(max_length=12, choices=Plan.choices, default=Plan.FREE)
    plan_expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.company_name

    @property
    def has_paid_plan(self):
        return self.plan != self.Plan.FREE and (not self.plan_expires_at or self.plan_expires_at > timezone.now())


class Job(models.Model):
    class JobType(models.TextChoices):
        FULL_TIME = "full_time", "Full time"
        PART_TIME = "part_time", "Part time"
        DAILY = "daily", "Daily shift"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"

    class SalaryPeriod(models.TextChoices):
        MONTH = "month", "Per month"
        DAY = "day", "Per day"
        HOUR = "hour", "Per hour"
        PROJECT = "project", "Per project"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        CLOSED = "closed", "Closed"
        REJECTED = "rejected", "Rejected"

    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name="jobs")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="jobs")
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title_kn = models.CharField(max_length=150)
    title_en = models.CharField(max_length=150)
    description_kn = models.TextField()
    description_en = models.TextField()
    job_type = models.CharField(max_length=15, choices=JobType.choices)
    salary_min = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    salary_max = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    salary_period = models.CharField(max_length=10, choices=SalaryPeriod.choices, default=SalaryPeriod.MONTH)
    vacancies = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    city = models.CharField(max_length=80, db_index=True)
    area = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=6, blank=True)
    address = models.TextField(blank=True)
    contact_phone = models.CharField(max_length=10)
    requirements = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PUBLISHED, db_index=True)
    is_featured = models.BooleanField(default=False)
    is_urgent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-is_featured", "-created_at"]
        indexes = [models.Index(fields=["status", "city", "-created_at"])]

    def __str__(self):
        return f"{self.title_en} – {self.employer.company_name}"

    def get_absolute_url(self):
        return reverse("jobs:detail", kwargs={"public_id": self.public_id})

    @property
    def is_open(self):
        return self.status == self.Status.PUBLISHED and (not self.expires_at or self.expires_at > timezone.now())

    @property
    def location(self):
        return ", ".join(filter(None, [self.area, self.city]))


class Application(models.Model):
    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        REVIEWED = "reviewed", "Reviewed"
        SHORTLISTED = "shortlisted", "Shortlisted"
        REJECTED = "rejected", "Rejected"
        HIRED = "hired", "Hired"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    note = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.APPLIED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["job", "applicant"], name="one_application_per_job")]

    def __str__(self):
        return f"{self.applicant} → {self.job}"


class JobReport(models.Model):
    class Reason(models.TextChoices):
        FAKE = "fake", "Fake job"
        FEE = "fee", "Asking candidate for money"
        WRONG = "wrong", "Incorrect information"
        ABUSE = "abuse", "Abusive or discriminatory"
        OTHER = "other", "Other"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_reports")
    reason = models.CharField(max_length=12, choices=Reason.choices)
    details = models.TextField(blank=True)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["job", "reporter"], name="one_report_per_user_job")]


class Payment(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name="payments")
    plan = models.CharField(max_length=12, choices=EmployerProfile.Plan.choices)
    amount_paise = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.CREATED)
    gateway_order_id = models.CharField(max_length=100, unique=True)
    gateway_payment_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.employer} {self.plan} ₹{self.amount_paise / 100:.2f}"
