from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponseRedirect


class CanonicalLocalHostMiddleware:
    """Keep development cookies on one hostname (127.0.0.1 or localhost)."""

    LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG:
            configured = urlsplit(settings.SITE_URL)
            request_host = urlsplit(f"//{request.get_host()}")
            if (
                configured.hostname in self.LOCAL_HOSTS
                and request_host.hostname in self.LOCAL_HOSTS
                and request_host.netloc != configured.netloc
            ):
                target = configured._replace(path=request.path, query=request.META.get("QUERY_STRING", ""), fragment="")
                return HttpResponseRedirect(target.geturl())
        return self.get_response(request)
