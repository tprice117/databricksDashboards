from django.contrib.messages import get_messages
from django.template.loader import render_to_string
from django.utils.deprecation import MiddlewareMixin


class HtmxMessageMiddleware(MiddlewareMixin):
    """
    Middleware to handle HTMX requests and append Django messages to the response.

    This middleware checks if the request is an HTMX request and if the response
    status code is not a redirection (300-399) and does not already contain an
    "HX-Redirect" header. If these conditions are met, it appends the rendered
    Django messages to the response.

    Methods:
        process_response(request, response):
            Processes the response to append Django messages if the request is an HTMX request.

    Args:
        request (HttpRequest): The HTTP request object.
        response (HttpResponse): The HTTP response object.

    Returns:
        HttpResponse: The modified HTTP response object with appended Django messages if applicable.
    """

    def process_response(self, request, response):
        if (
            "HX-Request" in request.headers
            and not 300 <= response.status_code < 400
            and "HX-Redirect" not in response.headers
        ):
            response.write(
                render_to_string(
                    "djangomessages.html",
                    {"messages": get_messages(request)},
                )
            )
        return response
