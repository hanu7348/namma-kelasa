from django.contrib import admin

from .models import Application, Category, EmployerProfile, Job, JobReport, Payment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("icon", "name_en", "name_kn", "is_active")
    prepopulated_fields = {"slug": ("name_en",)}


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ("company_name", "city", "is_verified", "plan", "plan_expires_at")
    list_filter = ("is_verified", "plan", "city")
    search_fields = ("company_name", "user__email", "gstin")
    actions = ["verify_employers"]

    @admin.action(description="Mark selected employers as verified")
    def verify_employers(self, request, queryset):
        queryset.update(is_verified=True)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title_en", "employer", "city", "job_type", "status", "is_featured", "created_at")
    list_filter = ("status", "job_type", "is_featured", "is_urgent", "city", "category")
    search_fields = ("title_en", "title_kn", "employer__company_name", "contact_phone")
    readonly_fields = ("public_id", "created_at", "updated_at")
    actions = ["publish", "close"]

    @admin.action(description="Publish selected jobs")
    def publish(self, request, queryset):
        queryset.update(status=Job.Status.PUBLISHED)

    @admin.action(description="Close selected jobs")
    def close(self, request, queryset):
        queryset.update(status=Job.Status.CLOSED)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("applicant", "job", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("applicant__email", "applicant__full_name", "job__title_en")


@admin.register(JobReport)
class JobReportAdmin(admin.ModelAdmin):
    list_display = ("job", "reporter", "reason", "resolved", "created_at")
    list_filter = ("reason", "resolved")
    actions = ["resolve"]

    @admin.action(description="Mark selected reports resolved")
    def resolve(self, request, queryset):
        queryset.update(resolved=True)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("employer", "plan", "amount_paise", "status", "created_at", "paid_at")
    list_filter = ("status", "plan")
    readonly_fields = ("gateway_order_id", "gateway_payment_id", "created_at", "paid_at")
