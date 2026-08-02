from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import OTPChallenge, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    ordering = ("email",)
    list_display = ("email", "full_name", "role", "is_staff")
    search_fields = ("email", "full_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "role", "preferred_language", "resume")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "full_name", "password1", "password2")}),)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "resume":
            kwargs["widget"] = forms.FileInput(attrs={"accept": ".pdf,.doc,.docx"})
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(OTPChallenge)
class OTPChallengeAdmin(admin.ModelAdmin):
    list_display = ("email", "purpose", "created_at", "expires_at", "attempts", "consumed_at")
    search_fields = ("email",)
    readonly_fields = ("code_hash", "created_at")
