import datetime
import os
import random
import string
import uuid
from typing import List

import mailchimp_marketing as MailchimpMarketing
import mailchimp_transactional as MailchimpTransactional
import stripe
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_delete, post_save, pre_save
from django.template.loader import render_to_string
from intercom.client import Client

# import pandas as pd
from .pricing_ml.pricing import Price_Model

stripe.api_key = settings.STRIPE_SECRET_KEY
mailchimp = MailchimpTransactional.Client("md-U2XLzaCVVE24xw3tMYOw9w")
