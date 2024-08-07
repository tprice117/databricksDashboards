import logging

from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)
from django.shortcuts import render


@login_required(login_url="/admin/login/")
def command_center(request):
    return render(
        request,
        "dashboards/index.html",
    )
