from threading import local

__all__ = ["get_request", "AuthorDefaultBackendMiddleware"]
_thread_locals = local()


def get_request():
    """Get request stored in current thread"""
    return getattr(_thread_locals, "request", None)


def set_user(user):
    """Sets the current user in request stored in current thread"""
    request = get_request()
    if request:
        setattr(request, "user", user)


class SaveAuthorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        response = self.get_response(request)
        _thread_locals.request = None
        return response
