from django.conf import settings


UI_TEXT = {
    "kn": {
        "brand": "ನಮ್ಮ ಕೆಲಸ", "jobs": "ಉದ್ಯೋಗಗಳು", "post_job": "ಉದ್ಯೋಗ ಪ್ರಕಟಿಸಿ",
        "dashboard": "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್", "login": "ಲಾಗಿನ್", "logout": "ಲಾಗ್ ಔಟ್",
        "search": "ಹುಡುಕಿ", "profile": "ಪ್ರೊಫೈಲ್", "plans": "ಪ್ಲಾನ್‌ಗಳು",
        "apply": "ಈಗ ಅರ್ಜಿ ಹಾಕಿ", "verified": "ಪರಿಶೀಲಿಸಲಾಗಿದೆ", "featured": "ಪ್ರಮುಖ",
        "urgent": "ತುರ್ತು", "salary": "ಸಂಬಳ", "location": "ಸ್ಥಳ", "report": "ವರದಿ ಮಾಡಿ",
    },
    "en": {
        "brand": "Namma Kelasa", "jobs": "Jobs", "post_job": "Post a job",
        "dashboard": "Dashboard", "login": "Login", "logout": "Log out",
        "search": "Search", "profile": "Profile", "plans": "Plans",
        "apply": "Apply now", "verified": "Verified", "featured": "Featured",
        "urgent": "Urgent", "salary": "Salary", "location": "Location", "report": "Report",
    },
}


def site_context(request):
    lang = request.session.get("lang", settings.DEFAULT_LANGUAGE)
    if lang not in UI_TEXT:
        lang = "kn"
    return {"lang": lang, "other_lang": "en" if lang == "kn" else "kn", "ui": UI_TEXT[lang]}
