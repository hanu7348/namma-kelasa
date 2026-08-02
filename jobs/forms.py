import re

from django import forms
from django.db.models import Q

from accounts.forms import validate_resume_contents

from .models import Application, EmployerProfile, Job, JobReport


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            else:
                field.widget.attrs.setdefault("class", "form-control")


class JobSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Search")
    city = forms.CharField(required=False, label="City")
    category = forms.CharField(required=False)
    job_type = forms.ChoiceField(required=False, choices=(("", "All types"),) + tuple(Job.JobType.choices))

    def filter(self, queryset):
        if not self.is_valid():
            return queryset
        data = self.cleaned_data
        if data.get("q"):
            queryset = queryset.filter(
                Q(title_kn__icontains=data["q"])
                | Q(title_en__icontains=data["q"])
                | Q(description_kn__icontains=data["q"])
                | Q(description_en__icontains=data["q"])
                | Q(employer__company_name__icontains=data["q"])
            )
        if data.get("city"):
            queryset = queryset.filter(Q(city__icontains=data["city"]) | Q(area__icontains=data["city"]))
        if data.get("category"):
            queryset = queryset.filter(category__slug=data["category"])
        if data.get("job_type"):
            queryset = queryset.filter(job_type=data["job_type"])
        return queryset


class JobForm(StyledModelForm):
    class Meta:
        model = Job
        fields = [
            "category", "title_kn", "title_en", "description_kn", "description_en",
            "job_type", "salary_min", "salary_max", "salary_period", "vacancies",
            "city", "area", "pincode", "address", "contact_phone", "requirements",
            "is_urgent", "expires_at",
        ]
        widgets = {"expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"}), "description_kn": forms.Textarea(attrs={"rows": 5}), "description_en": forms.Textarea(attrs={"rows": 5})}

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("salary_min") and cleaned.get("salary_max") and cleaned["salary_min"] > cleaned["salary_max"]:
            self.add_error("salary_max", "Maximum salary must be greater than minimum salary.")
        return cleaned

    def clean_contact_phone(self):
        phone = re.sub(r"\D", "", self.cleaned_data["contact_phone"])
        if not re.fullmatch(r"[6-9]\d{9}", phone):
            raise forms.ValidationError("Enter a valid 10-digit Indian mobile number.")
        return phone


class EmployerProfileForm(StyledModelForm):
    class Meta:
        model = EmployerProfile
        fields = ["company_name", "contact_person", "city", "address", "website", "gstin"]


class ApplicationForm(StyledModelForm):
    resume = forms.FileField(
        required=False,
        label="ರೆಸ್ಯೂಮ್ / Resume (optional)",
        help_text="PDF, DOC ಅಥವಾ DOCX · ಗರಿಷ್ಠ 5 MB. ಹೊಸ file ಆಯ್ಕೆ ಮಾಡದಿದ್ದರೆ profile resume ಬಳಸಲಾಗುತ್ತದೆ.",
        widget=forms.FileInput(attrs={"accept": ".pdf,.doc,.docx", "class": "form-control resume-input"}),
    )

    class Meta:
        model = Application
        fields = ["note"]
        labels = {"note": "ಸಂದೇಶ / Message (optional)"}
        widgets = {"note": forms.Textarea(attrs={"rows": 3, "placeholder": "ನಿಮ್ಮ ಅನುಭವ ಅಥವಾ ಲಭ್ಯತೆ ತಿಳಿಸಿ"})}

    def clean_resume(self):
        return validate_resume_contents(self.cleaned_data.get("resume"))


class JobReportForm(StyledModelForm):
    class Meta:
        model = JobReport
        fields = ["reason", "details"]
        widgets = {"details": forms.Textarea(attrs={"rows": 3})}
