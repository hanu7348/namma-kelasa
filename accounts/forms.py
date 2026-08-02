import os
import zipfile

from django import forms

from .models import User


def validate_resume_contents(upload):
    if not upload:
        return upload
    extension = os.path.splitext(upload.name)[1].lower()
    if extension not in {".pdf", ".doc", ".docx"}:
        raise forms.ValidationError("Upload a PDF, DOC or DOCX resume.")
    if upload.size > 5 * 1024 * 1024:
        raise forms.ValidationError("Resume must be 5 MB or smaller.")
    try:
        header = upload.read(8)
        upload.seek(0)
        if extension == ".pdf" and not header.startswith(b"%PDF-"):
            raise forms.ValidationError("This file is not a valid PDF.")
        if extension == ".doc" and header != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            raise forms.ValidationError("This file is not a valid DOC document.")
        if extension == ".docx":
            with zipfile.ZipFile(upload) as archive:
                names = set(archive.namelist())
                if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                    raise forms.ValidationError("This file is not a valid DOCX document.")
    except (OSError, zipfile.BadZipFile):
        raise forms.ValidationError("The resume file is damaged or unsupported.")
    finally:
        upload.seek(0)
    return upload


class StyledFormMixin:
    def style_fields(self):
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class EmailForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(label="ಇಮೇಲ್ ವಿಳಾಸ / Email address", max_length=254)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()
        self.fields["email"].widget.attrs.update({"placeholder": "you@example.com", "autocomplete": "email", "autofocus": True})

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class VerifyOTPForm(StyledFormMixin, forms.Form):
    code = forms.CharField(label="OTP", min_length=6, max_length=6)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()
        self.fields["code"].widget.attrs.update({"inputmode": "numeric", "placeholder": "6-digit OTP", "autocomplete": "one-time-code"})


class CompleteProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "role", "preferred_language", "resume"]
        labels = {
            "full_name": "ಹೆಸರು / Name",
            "role": "ನಿಮ್ಮ ಪಾತ್ರ / Role",
            "preferred_language": "ಭಾಷೆ / Language",
            "resume": "ರೆಸ್ಯೂಮ್ / Resume (optional)",
        }
        help_texts = {"resume": "PDF, DOC ಅಥವಾ DOCX · ಗರಿಷ್ಠ 5 MB"}
        widgets = {"resume": forms.FileInput(attrs={"accept": ".pdf,.doc,.docx", "class": "form-control resume-input"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()
        self.fields["resume"].widget.attrs.update({"accept": ".pdf,.doc,.docx", "class": "form-control resume-input"})

    def clean_resume(self):
        return validate_resume_contents(self.cleaned_data.get("resume"))
