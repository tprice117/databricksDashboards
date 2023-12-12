import datetime
import os
import random
import string
from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save, post_save, post_delete
import uuid
import stripe
# from simple_salesforce import Salesforce
from multiselectfield import MultiSelectField
from api.utils.auth0 import create_user, get_password_change_url, get_user_data, get_user_from_email, delete_user, invite_user
from api.utils.google_maps import geocode_address
import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError
from intercom.client import Client
import mailchimp_transactional as MailchimpTransactional
# import pandas as pd
from .pricing_ml.pricing import Price_Model
from django.core.files.storage import default_storage
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string

stripe.api_key = settings.STRIPE_SECRET_KEY
mailchimp = MailchimpTransactional.Client("md-U2XLzaCVVE24xw3tMYOw9w")

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
       abstract = True

class Seller(BaseModel):
    open_day_choices = (
       ('MONDAY', 'MONDAY'), 
       ('TUESDAY', 'TUESDAY'), 
       ('WEDNESDAY', 'WEDNESDAY'), 
       ('THURSDAY', 'THURSDAY'), 
       ('FRIDAY', 'FRIDAY'), 
       ('SATURDAY', 'SATURDAY'), 
       ('SUNDAY', 'SUNDAY')
    )
     
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=40)
    website = models.URLField(blank=True, null=True)
    # START: Communicaton fields.
    order_email = models.CharField(max_length=255, blank=True, null=True)
    order_phone = models.CharField(max_length=10, blank=True, null=True)
    # END: Communicaton fields.
    type = models.CharField(max_length=255, choices=[('Broker', 'Broker'), ('Compost facility', 'Compost facility'), ('Delivery', 'Delivery'), ('Equipment', 'Equipment'), ('Fencing', 'Fencing'), ('Industrial', 'Industrial'), ('Junk', 'Junk'), ('Landfill', 'Landfill'), ('Mover', 'Mover'), ('MRF', 'MRF'), ('Other recycler', 'Other recycler'), ('Paint recycler', 'Paint recycler'), ('Portable Storage', 'Portable Storage'), ('Portable Toilet', 'Portable Toilet'), ('Processor', 'Processor'), ('Roll-off', 'Roll-off'), ('Scrap yard', 'Scrap yard'), ('Tires', 'Tires')], blank=True, null=True)
    location_type = models.CharField(max_length=255, choices=[('Services', 'Services'), ('Disposal site', 'Disposal site')], blank=True, null=True)
    status = models.CharField(max_length=255, choices=[('Inactive', 'Inactive'), ('Inactive - Onboarding', 'Inactive - Onboarding'), ('Inactive - Pending approval', 'Inactive - Pending approval'), ('Active - under review', 'Active - under review'), ('Active', 'Active')], blank=True, null=True)
    lead_time = models.CharField(max_length=255, blank=True, null=True)
    type_display = models.CharField(max_length=255, choices=[('Landfill', 'Landfill'), ('MRF', 'MRF'), ('Industrial', 'Industrial'), ('Scrap yard', 'Scrap yard'), ('Compost facility', 'Compost facility'), ('Processor', 'Processor'), ('Paint recycler', 'Paint recycler'), ('Tires', 'Tires'), ('Other recycler', 'Other recycler'), ('Roll-off', 'Roll-off'), ('Mover', 'Mover'), ('Junk', 'Junk'), ('Delivery', 'Delivery'), ('Broker', 'Broker'), ('Equipment', 'Equipment')], blank=True, null=True)
    stripe_connect_id = models.CharField(max_length=255, blank=True, null=True)
    marketplace_display_name = models.CharField(max_length=255, blank=True, null=True)
    open_days = MultiSelectField(max_length=255, choices = open_day_choices, max_choices=7, blank=True, null=True)
    open_time = models.TimeField(blank=True, null=True)
    close_time = models.TimeField(blank=True, null=True)
    lead_time_hrs = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    announcement = models.TextField(blank=True, null=True)
    live_menu_is_active = models.BooleanField(default=False)
    location_logo_url = models.URLField(blank=True, null=True)
    downstream_insurance_requirements_met = models.BooleanField(default=False)
    badge = models.CharField(max_length=255, choices=[('New', 'New'), ('Pro', 'Pro'), ('Platinum', 'Platinum')], blank=True, null=True)
    salesforce_seller_id = models.CharField(max_length=255, blank=True, null=True)
    about_us = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class SellerLocation(BaseModel):
    def get_file_path(instance, filename):
        ext = filename.split('.')[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return filename

    seller = models.ForeignKey(Seller, models.CASCADE, related_name='seller_locations')
    name = models.CharField(max_length=255)
    street = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=80)
    latitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)
    longitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)
    stripe_connect_account_id = models.CharField(max_length=255, blank=True, null=True)
    # START: Check fields.
    payee_name = models.CharField(max_length=255, blank=True, null=True)
    # END: Check fields.
    # START: Communicaton fields.
    order_email = models.CharField(max_length=255, blank=True, null=True)
    order_phone = models.CharField(max_length=10, blank=True, null=True)
    # END: Communicaton fields.
    # START: Insurance and tax fields.
    gl_coi = models.FileField(upload_to=get_file_path, blank=True, null=True)
    gl_coi_expiration_date = models.DateField(blank=True, null=True)
    gl_limit = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    auto_coi = models.FileField(upload_to=get_file_path, blank=True, null=True)
    auto_coi_expiration_date = models.DateField(blank=True, null=True)
    auto_limit = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    workers_comp_coi = models.FileField(upload_to=get_file_path, blank=True, null=True)
    workers_comp_coi_expiration_date = models.DateField(blank=True, null=True)
    workers_comp_limit = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    w9 = models.FileField(upload_to=get_file_path, blank=True, null=True)
    # END: Insurance and tax fields.

    def __str__(self):
        return self.name

    def pre_save(sender, instance, *args, **kwargs):
        latitude, longitude = geocode_address(f"{instance.street} {instance.city} {instance.state} {instance.postal_code}")
        instance.latitude = latitude or 0
        instance.longitude = longitude or 0

class SellerLocationMailingAddress(BaseModel):
    seller_location = models.OneToOneField(
        SellerLocation, 
        models.CASCADE,
        related_name='mailing_address'
    )
    street = models.TextField()
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=80)
    latitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)
    longitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True) 

    def pre_save(sender, instance, *args, **kwargs):
        latitude, longitude = geocode_address(f"{instance.street} {instance.city} {instance.state} {instance.postal_code}")
        instance.latitude = latitude or 0
        instance.longitude = longitude or 0

class UserGroup(BaseModel):
    class TaxExemptStatus(models.TextChoices):
        NONE = 'none'
        EXEMPT = 'exempt'
        REVERSE = 'reverse'

    COMPLIANCE_STATUS_CHOICES = (
        ("NOT_REQUIRED", "Not Required"),
        ("REQUESTED", "Requested"),
        ("IN-PROGRESS", "In-Progress"),
        ("NEEDS_REVIEW", "Needs Review"),
        ("APPROVED", "Approved"),
    )

    seller = models.OneToOneField(Seller, models.DO_NOTHING, blank=True, null=True)
    name = models.CharField(max_length=255)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    pay_later = models.BooleanField(default=False)
    autopay= models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    share_code = models.CharField(max_length=6, blank=True)
    parent_account_id = models.CharField(max_length=255, blank=True, null=True)
    credit_line_limit = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    compliance_status = models.CharField(max_length=20, choices=COMPLIANCE_STATUS_CHOICES, default="NOT_REQUIRED")
    tax_exempt_status = models.CharField(max_length=20, choices=TaxExemptStatus.choices, default=TaxExemptStatus.NONE)

    def __str__(self):
        return self.name
    
    def post_create(sender, instance, created, **kwargs):
        if created:
            # Generate unique share code.
            share_code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            while share_code in UserGroup.objects.values_list('share_code', flat=True):
                share_code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            instance.share_code = share_code
            
            # Create stripe customer.
            # customer = stripe.Customer.create()
            # instance.stripe_customer_id = customer.id
            instance.save()

class UserGroupBilling(BaseModel):
    user_group = models.OneToOneField(
        UserGroup, 
        models.CASCADE,
        related_name='billing'
    )
    email = models.EmailField()
    # phone = models.CharField(max_length=40, blank=True, null=True)
    tax_id = models.CharField(max_length=255, blank=True, null=True)
    street = models.TextField()
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=80)
    latitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)
    longitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True) 

    def pre_save(sender, instance, *args, **kwargs):
        latitude, longitude = geocode_address(f"{instance.street} {instance.city} {instance.state} {instance.postal_code}")
        instance.latitude = latitude or 0
        instance.longitude = longitude or 0

class UserAddressType(BaseModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class User(BaseModel):
    user_group = models.ForeignKey(UserGroup, models.CASCADE, blank=True, null=True)
    user_id = models.CharField(max_length=255, blank=True)
    mailchip_id = models.CharField(max_length=255, blank=True, null=True)
    intercom_id = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=40, blank=True, null=True)
    email = models.CharField(max_length=255, unique=True)
    photo_url = models.TextField(blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    device_token= models.CharField(max_length=255, blank=True, null=True)
    is_admin = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    salesforce_contact_id = models.CharField(max_length=255, blank=True, null=True)
    salesforce_seller_location_id = models.CharField(max_length=255, blank=True, null=True)
    terms_accepted = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        if not self.user_id:
            # Create or attach to Auth0 user.
            user_id = get_user_from_email(self.email)

            if user_id:
                # User already exists in Auth0.
                self.user_id = user_id
                created_by_downstream_team = False
            else:
                # Create user in Auth0.
                self.user_id = create_user(self.email)
                created_by_downstream_team = True

            # Send invite email.
            if created_by_downstream_team:
                invite_user(self)

            # Send email to internal team. Only on our PROD environment.
            if settings.ENVIRONMENT == "TEST":
                try:
                    mailchimp.messages.send({"message": {
                        "headers": {
                            "reply-to": self.email,
                        },
                        "from_name": "Downstream",
                        "from_email": "noreply@trydownstream.io",
                        "to": [{"email": "sales@trydownstream.io"}],
                        "subject": "New User App Signup",
                        "track_opens": True,
                        "track_clicks": True,
                        "text": "Woohoo! A new user signed up for the app. The email on their account is: [" + self.email + "]. This was created by: " + ("[DOWNSTREAM TEAM]" if created_by_downstream_team else "[]") + ".",
                    }})
                except:
                    print("An exception occurred.")
            
        super(User, self).save(*args, **kwargs)  

    def post_delete(sender, instance, **kwargs):
        # Delete auth0 user.
        try:
            delete_user(instance.user_id)
        except Exception as e:
            print("this didn't work")
            print(e)
            pass

        # TODO: Delete mailchimp user.

        # Delete intercom user.
        try:
            intercom = Client(personal_access_token='dG9rOjVlZDVhNWRjXzZhOWNfNGYwYl9hN2MyX2MzZmYzNzBmZDhkNDoxOjA=')
            contact = intercom.leads.find(id=instance.intercom_id)
            intercom.leads.delete(contact)
        except Exception as e:
            print('something went wrong with intercom')
            print(e)
            pass

class UserAddress(BaseModel):
    user_group = models.ForeignKey(UserGroup, models.CASCADE, blank=True, null=True)
    user = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    user_address_type = models.ForeignKey(UserAddressType, models.CASCADE, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    project_id = models.CharField(max_length=50, blank=True, null=True)
    street = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=80)
    latitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)
    longitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True)
    autopay = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    child_account_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name or "[No name]"
    
    def formatted_address(self):
        return f'{self.street} {self.city}, {self.state} {self.postal_code}'
    
    def pre_save(sender, instance, *args, **kwargs):
        # Populate latitude and longitude.
        latitude, longitude = geocode_address(f"{instance.street} {instance.city} {instance.state} {instance.postal_code}")
        instance.latitude = latitude or 0
        instance.longitude = longitude or 0

        # Populate Stripe Customer ID, if not already populated.
        if not instance.stripe_customer_id:
            customer = stripe.Customer.create()
            instance.stripe_customer_id = customer.id
        else:
            customer = stripe.Customer.retrieve(instance.stripe_customer_id)

        # Populate Stripe Customer ID.
        customer = stripe.Customer.modify(
            customer.id,
            name = (instance.user_group.name) + " | " + instance.formatted_address(),
            email = instance.user_group.billing.email if hasattr(instance.user_group, 'billing') else instance.user.email,
            # phone = instance.user_group.billing.phone if hasattr(instance.user_group, 'billing') else instance.user.phone,
            shipping = {
                "name": (instance.user_group.name) + " | " + instance.formatted_address(),
                "address": {
                    "line1": instance.street,
                    "city": instance.city,
                    "state": instance.state,
                    "postal_code": instance.postal_code,
                    "country": instance.country,
                },
            },
            address = {
                "line1": instance.user_group.billing.street if hasattr(instance.user_group, 'billing') else instance.street,
                "city": instance.user_group.billing.city if hasattr(instance.user_group, 'billing') else instance.city,
                "state": instance.user_group.billing.state if hasattr(instance.user_group, 'billing') else instance.state,
                "postal_code": instance.user_group.billing.postal_code if hasattr(instance.user_group, 'billing') else instance.postal_code,
                "country": instance.user_group.billing.country if hasattr(instance.user_group, 'billing') else instance.country,
            },
            metadata={
                'user_group_id': str(instance.user_group.id),
                'user_address_id': str(instance.id),
                'user_id': str(instance.user.id),
            },
            tax_exempt = instance.user_group.tax_exempt_status if hasattr(instance.user_group, 'billing') else UserGroup.TaxExemptStatus.NONE,
        )

class UserGroupUser(BaseModel):
    user_group = models.ForeignKey(UserGroup, models.CASCADE)
    user = models.ForeignKey(User, models.CASCADE)

    def __str__(self):
        return f'{self.user_group.name} - {self.user.email}'

class UserUserAddress(BaseModel):
    user = models.ForeignKey(User, models.CASCADE)
    user_address = models.ForeignKey(UserAddress, models.CASCADE)

    def __str__(self):
        return f'{self.user.email} - {self.user_address.street}'
    
class UserSellerLocation(BaseModel):
    user = models.ForeignKey(User, models.CASCADE)
    seller_location = models.ForeignKey(SellerLocation, models.CASCADE)

    def __str__(self):
        return f'{self.user.email} - {self.seller_location.name}'
    
class UserSellerReview(BaseModel): #added this model 2/25/2023 by Dylan
    seller = models.ForeignKey(Seller, models.DO_NOTHING, related_name='user_seller_review')
    user = models.ForeignKey(User, models.DO_NOTHING, related_name='user_seller_review')
    title = models.CharField(max_length=255)
    rating = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f'{self.seller.name} - {self.rating if self.rating else ""}'

class MainProductCategory(BaseModel):
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True, null=True)
    image = models.TextField(blank=True, null=True)
    icon = models.TextField(blank=True, null=True)
    sort = models.IntegerField()
    main_product_category_code = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

class MainProductCategoryInfo(BaseModel):
    name = models.CharField(max_length=80)
    main_product_category = models.ForeignKey(MainProductCategory, models.CASCADE)
    sort = models.IntegerField()

    def __str__(self):
        return self.name

class MainProduct(BaseModel):
    name = models.CharField(max_length=80)
    cubic_yards = models.IntegerField(blank=True, null=True)
    ar_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image_del = models.TextField(blank=True, null=True)
    main_product_category = models.ForeignKey(MainProductCategory, models.CASCADE)
    sort = models.IntegerField()
    included_tonnage_quantity = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    price_per_additional_ton = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    max_tonnage_quantity = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    max_rate = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    included_rate_quantity = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    main_product_code = models.CharField(max_length=255, blank=True, null=True) 
    has_service = models.BooleanField(default=False)
    has_rental = models.BooleanField(default=False)
    has_material = models.BooleanField(default=False)
    
    def __str__(self):
        return f'{self.main_product_category.name} - {self.name}'

class MainProductInfo(BaseModel):
    name = models.CharField(max_length=80)
    main_product = models.ForeignKey(MainProduct, models.CASCADE)
    sort = models.IntegerField()

    def __str__(self):
        return self.name

class AddOn(BaseModel):
    main_product = models.ForeignKey(MainProduct, models.CASCADE)
    name = models.CharField(max_length=80)
    sort = models.DecimalField(max_digits=18, decimal_places=0)

    def __str__(self):
        return f'{self.main_product.name} - {self.name}'

class AddOnChoice(BaseModel):
    name = models.CharField(max_length=80)
    add_on = models.ForeignKey(AddOn, models.CASCADE)

    def __str__(self):
        return f'{self.add_on.main_product.name} - {self.add_on.name} - {self.name}'
    
class MainProductAddOn(BaseModel):
    main_product = models.ForeignKey(MainProduct, models.CASCADE)
    add_on = models.ForeignKey(AddOn, models.CASCADE)

    def __str__(self):
        return f'{self.main_product.name} - {self.add_on.name}'
    
class WasteType(BaseModel):
    name = models.CharField(max_length=80)

    def __str__(self):
        return self.name
    
class MainProductWasteType(BaseModel):
    waste_type = models.ForeignKey(WasteType, models.CASCADE)
    main_product = models.ForeignKey(MainProduct, models.CASCADE)

    def __str__(self):
        return f'{self.main_product.name} - {self.waste_type.name}'
    
    class Meta:
        unique_together = ('waste_type', 'main_product',)

class Product(BaseModel):
    product_code = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    main_product = models.ForeignKey(MainProduct, models.CASCADE)
    removal_price = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)

    def __str__(self):
        add_on_choices = ProductAddOnChoice.objects.filter(product=self)
        return f'{self.main_product.name} {"-" if add_on_choices.count() > 0 else ""} {",".join(str(add_on_choice.name) for add_on_choice in add_on_choices)}'

class SellerProduct(BaseModel):
    product = models.ForeignKey(Product, models.CASCADE, related_name='seller_products')
    seller = models.ForeignKey(Seller, models.CASCADE, related_name='seller_products')
    active = models.BooleanField(default=True)
   
    def __str__(self):
        return self.product.main_product.name + ' - ' + (self.product.product_code or "") + ' - ' + self.seller.name
    
    class Meta:
        unique_together = ('product', 'seller',)

class SellerProductSellerLocation(BaseModel):
    seller_product = models.ForeignKey(SellerProduct, models.CASCADE, related_name='seller_location_seller_products')
    seller_location = models.ForeignKey(SellerLocation, models.CASCADE, related_name='seller_location_seller_products')
    active = models.BooleanField(default=True)
    total_inventory = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True) # Added 2/20/2023 Total Quantity input by seller of product offered
    min_price = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    max_price = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    service_radius = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    delivery_fee = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    removal_fee = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    fuel_environmental_markup = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)

    class Meta:
        unique_together = ('seller_product', 'seller_location',)

    def __str__(self):
        return f'{self.seller_location.name if self.seller_location and self.seller_location.name else ""} - {self.seller_product.product.main_product.name if self.seller_product and self.seller_product.product and self.seller_product.product.main_product and self.seller_product.product.main_product.name else ""}'
    
    def post_save(sender, instance, created, **kwargs):
        # Create/delete Service.
        if not hasattr(instance, 'service') and instance.seller_product.product.main_product.has_service :
            SellerProductSellerLocationService.objects.create(seller_product_seller_location=instance)
        elif hasattr(instance, 'service') and not instance.seller_product.product.main_product.has_service:
            instance.service.delete()
        
        # Create/delete Rental.
        if not hasattr(instance, 'rental') and instance.seller_product.product.main_product.has_rental:
            SellerProductSellerLocationRental.objects.create(seller_product_seller_location=instance)
        elif hasattr(instance, 'rental') and not instance.seller_product.product.main_product.has_rental:
            instance.rental.delete()

        # Create/delete Material.
        if not hasattr(instance, 'material') and instance.seller_product.product.main_product.has_material:
            SellerProductSellerLocationMaterial.objects.create(seller_product_seller_location=instance)
        elif hasattr(instance, 'material') and not instance.seller_product.product.main_product.has_material:
            instance.material.delete()

class ServiceRecurringFrequency(BaseModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class MainProductServiceRecurringFrequency(BaseModel):
    main_product = models.ForeignKey(MainProduct, models.PROTECT)
    service_recurring_frequency = models.ForeignKey(
        ServiceRecurringFrequency,
        models.PROTECT
    )

    def __str__(self):
        return f'{self.main_product.name} - {self.service_recurring_frequency.name}'  
   
class SellerProductSellerLocationService(BaseModel):
    seller_product_seller_location = models.OneToOneField(
        SellerProductSellerLocation,
        on_delete=models.CASCADE,
        related_name='service'
    )
    price_per_mile = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    flat_rate_price = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return self.seller_product_seller_location.seller_location.name
    
    def post_save(sender, instance, created, **kwargs):
        # Ensure all service recurring frequencies are created.
        for service_recurring_frequency in MainProductServiceRecurringFrequency.objects.filter(main_product=instance.seller_product_seller_location.seller_product.product.main_product):
            if not SellerProductSellerLocationServiceRecurringFrequency.objects.filter(
                seller_product_seller_location_service=instance,
                main_product_service_recurring_frequency=service_recurring_frequency
            ).exists():
                SellerProductSellerLocationServiceRecurringFrequency.objects.create(
                    seller_product_seller_location_service=instance,
                    main_product_service_recurring_frequency=service_recurring_frequency
                )

        # Ensure all "stale" service recurring frequencies are deleted.
        for seller_product_seller_location_service_recurring_frequency in SellerProductSellerLocationServiceRecurringFrequency.objects.filter(
            seller_product_seller_location_service=instance
        ):
            if not MainProductServiceRecurringFrequency.objects.filter(
                main_product=seller_product_seller_location_service_recurring_frequency.main_product_service_recurring_frequency.main_product,
                service_recurring_frequency=seller_product_seller_location_service_recurring_frequency.main_product_service_recurring_frequency.service_recurring_frequency
            ).exists():
                seller_product_seller_location_service_recurring_frequency.delete()

class SellerProductSellerLocationServiceRecurringFrequency(BaseModel):
    seller_product_seller_location_service = models.ForeignKey(
        SellerProductSellerLocationService, 
        models.PROTECT
    )
    main_product_service_recurring_frequency = models.ForeignKey(
        MainProductServiceRecurringFrequency, 
        models.PROTECT,
    )
    price = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        unique_together = ('seller_product_seller_location_service', 'main_product_service_recurring_frequency',)

    def __str__(self):
        return f'{self.seller_product_seller_location_service.seller_product_seller_location.seller_location.name} - {self.main_product_service_recurring_frequency.main_product.name}'
    
class SellerProductSellerLocationRental(BaseModel):
    seller_product_seller_location = models.OneToOneField(
        SellerProductSellerLocation,
        on_delete=models.CASCADE,
        related_name='rental'
    )
    included_days = models.IntegerField(default=0)
    price_per_day_included = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    price_per_day_additional = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    def __str__(self):
        return self.seller_product_seller_location.seller_location.name
    
class SellerProductSellerLocationMaterial(BaseModel):
    seller_product_seller_location = models.OneToOneField(
        SellerProductSellerLocation,
        on_delete=models.CASCADE,
        related_name='material'
    )

    def __str__(self):
        return self.seller_product_seller_location.seller_location.name
    
    def post_save(sender, instance, created, **kwargs):
        # Ensure all material waste type recurring frequencies are created. Only execute on create.
        if created:
            for main_product_waste_type in MainProductWasteType.objects.filter(main_product=instance.seller_product_seller_location.seller_product.product.main_product):
                if not SellerProductSellerLocationMaterialWasteType.objects.filter(
                    seller_product_seller_location_material=instance.seller_product_seller_location.material,
                    main_product_waste_type=main_product_waste_type
                ).exists():
                    SellerProductSellerLocationMaterialWasteType.objects.create(
                        seller_product_seller_location_material=instance.seller_product_seller_location.material,
                        main_product_waste_type=main_product_waste_type
                    )

        # Ensure all "stale" material waste type recurring frequencies are deleted.
        for seller_product_seller_location_material_waste_type in SellerProductSellerLocationMaterialWasteType.objects.filter(seller_product_seller_location_material=instance):
            if not MainProductWasteType.objects.filter(
                main_product=instance.seller_product_seller_location.seller_product.product.main_product,
                waste_type=seller_product_seller_location_material_waste_type.main_product_waste_type.waste_type
            ).exists():
                seller_product_seller_location_material_waste_type.delete()
    
class SellerProductSellerLocationMaterialWasteType(BaseModel):
    seller_product_seller_location_material = models.ForeignKey(
        SellerProductSellerLocationMaterial, 
        models.PROTECT,
        related_name='waste_types'
    )
    main_product_waste_type = models.ForeignKey(
        MainProductWasteType,
        models.PROTECT
    )
    price_per_ton = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tonnage_included = models.IntegerField(default=0)

    class Meta:
        unique_together = ('seller_product_seller_location_material', 'main_product_waste_type',)

class DayOfWeek(BaseModel):
    name = models.CharField(max_length=80)
    number = models.IntegerField()
    def __str__(self):
        return self.name    
    
class TimeSlot(BaseModel):
    name = models.CharField(max_length=80)
    start = models.TimeField()
    end = models.TimeField()

    def __str__(self):
        return self.name 

class OrderGroup(BaseModel):
    user = models.ForeignKey(User, models.PROTECT)
    user_address = models.ForeignKey(UserAddress, models.PROTECT)
    seller_product_seller_location = models.ForeignKey(SellerProductSellerLocation, models.PROTECT)
    waste_type = models.ForeignKey(WasteType, models.PROTECT, blank=True, null=True)
    time_slot = models.ForeignKey(TimeSlot, models.PROTECT, blank=True, null=True)
    access_details = models.TextField(blank=True, null=True)
    placement_details = models.TextField(blank=True, null=True)
    service_recurring_frequency = models.ForeignKey(ServiceRecurringFrequency, models.PROTECT, blank=True, null=True)
    preferred_service_days = models.ManyToManyField(DayOfWeek, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    take_rate = models.DecimalField(max_digits=18, decimal_places=2, default=30)
    tonnage_quantity = models.IntegerField(blank=True, null=True)
    delivery_fee = models.DecimalField(max_digits=18, decimal_places=2, default=0, blank=True, null=True)
    removal_fee = models.DecimalField(max_digits=18, decimal_places=2, default=0, blank=True, null=True)
    
    def __str__(self):
        return f'{self.user.user_group.name if self.user.user_group else ""} - {self.user.email} - {self.seller_product_seller_location.seller_location.seller.name}'

class OrderGroupService(BaseModel):
    order_group = models.OneToOneField(
        OrderGroup,
        on_delete=models.CASCADE,
        related_name='service'
    )
    rate = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    miles = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)

class OrderGroupRental(BaseModel):
    order_group = models.OneToOneField(
        OrderGroup,
        on_delete=models.CASCADE,
        related_name='rental'
    )
    included_days = models.IntegerField(default=0)
    price_per_day_included = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    price_per_day_additional = models.DecimalField(max_digits=18, decimal_places=2, default=0)

class OrderGroupMaterial(BaseModel):
    order_group = models.OneToOneField(
        OrderGroup,
        on_delete=models.CASCADE,
        related_name='material'
    )
    price_per_ton = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tonnage_included = models.IntegerField(default=0)

class Subscription(BaseModel):
    order_group = models.OneToOneField(OrderGroup, models.PROTECT)
    frequency = models.ForeignKey(ServiceRecurringFrequency, models.PROTECT, blank=True, null=True)
    service_day = models.ForeignKey(DayOfWeek, models.PROTECT, blank=True, null=True)
    length = models.IntegerField()
    subscription_number = models.CharField(max_length=255)
    interval_days = models.IntegerField(blank=True, null=True)
    length_days = models.IntegerField(blank=True, null=True) 
    
class ProductAddOnChoice(BaseModel):
    name = models.CharField(max_length=80)
    product = models.ForeignKey(Product, models.CASCADE, related_name='product_add_on_choices')
    add_on_choice = models.ForeignKey(AddOnChoice, models.CASCADE)

    def __str__(self):
        return f'{self.product.main_product.name} - {self.add_on_choice.add_on.name} - {self.add_on_choice.name}'
    
    class Meta:
        unique_together = ('product', 'add_on_choice',)

class DisposalLocation(BaseModel):
    name = models.CharField(max_length=255)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=80)
    latitude = models.DecimalField(max_digits=18, decimal_places=15)
    longitude = models.DecimalField(max_digits=18, decimal_places=15)

    def __str__(self):
        return self.name
    
class DisposalLocationWasteType(BaseModel):
    disposal_location = models.ForeignKey(DisposalLocation, models.CASCADE)
    waste_type = models.ForeignKey(WasteType, models.CASCADE)
    price_per_ton = models.DecimalField(max_digits=18, decimal_places=2)

    def __str__(self):
        return self.disposal_location.name + ' - ' + self.waste_type.name
    
class Order(BaseModel):
    class Type(models.TextChoices):
        DELIVERY = 'DELIVERY'
        SWAP = 'SWAP'
        REMOVAL = 'REMOVAL'
        AUTO_RENEWAL = 'AUTO_RENEWAL'
        ONE_TIME = 'ONE_TIME'

    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    INPROGRESS = "IN-PROGRESS"
    AWAITINGREQUEST = "Awaiting Request"
    CANCELLED = "CANCELLED"
    COMPLETE = "COMPLETE"

    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (SCHEDULED, "Scheduled"),
        (INPROGRESS, "In-Progress"),
        (AWAITINGREQUEST, "Awaiting Request"),
        (CANCELLED, "Cancelled"),
        (COMPLETE, "Complete"),
    )

    order_group = models.ForeignKey(OrderGroup, models.PROTECT, related_name='orders')
    disposal_location = models.ForeignKey(DisposalLocation, models.DO_NOTHING, blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    service_date = models.DateField()
    submitted_on = models.DateTimeField(blank=True, null=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    salesforce_order_id = models.CharField(max_length=255, blank=True, null=True)
    schedule_details = models.TextField(blank=True, null=True) #6.6.23 (Modified name to schedule_details from additional_schedule_details)
    price = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    order_type =  models.CharField(max_length=255, choices=[('Delivery', 'Delivery'), ('Automatic Renewal', 'Automatic Renewal'), ('Swap', 'Swap'),('Empty and Return','Empty and Return'),('Trip Charge/Dry Run','Trip Charge/Dry Run'),('Removal','Removal'),('On Demand','On Demand'),('Other','Other')], blank=True, null=True) #6.6.23
    included_weight_tons = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True) #6.6.23
    invoice_status = models.CharField(max_length=35, choices=[('Not yet invoiced', 'Not yet invoiced'), ('In draft', 'In draft'), ('Sent to customer','Sent to customer'),('Paid','Paid')], default=[0][0], blank=True, null=True) #6.6.23
    billing_comments_internal_use = models.TextField(blank=True, null=True) #6.6.23
    schedule_window = models.CharField(max_length=35, choices=[('Morning (7am-11am)','Morning (7am-11am)'),('Afternoon (12pm-4pm)','Afternoon (12pm-4pm)'),('Evening (5pm-8pm)','Evening (5pm-8pm)')], blank=True, null=True) #6.6.23
    supplier_payout_status = models.CharField(max_length=35, choices=[('Not yet paid', 'Not yet paid'), ('Process Payment', 'Process Payment'), ('Payout Processing Error','Payout Processing Error'),('Payout Completed','Payout Completed')], default=[0][0], blank=True, null=True) #6.6.23
    suppplier_payout_method = models.CharField(max_length=35, choices=[('Stripe Connect', 'Stripe Connect'), ('By Invoice', 'By Invoice'), ('Other','Other')], blank=True, null=True) #6.6.23
    tax_rate = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True) #6.6.23
    quantity = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True) #6.6.23
    unit_price = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True) #6.6.23
    payout_processing_error_comment = models.TextField(blank=True, null=True) #6.6.23
    __original_submitted_on = None

    def __init__(self, *args, **kwargs):
        super(Order, self).__init__(*args, **kwargs)
        self.__original_submitted_on = self.submitted_on
        self.__original_status = self.status

    def customer_price(self):
        order_line_items = OrderLineItem.objects.filter(order=self)
        return sum([order_line_item.rate * order_line_item.quantity * (1 + (order_line_item.platform_fee_percent / 100)) for order_line_item in order_line_items])
    
    def seller_price(self):
        order_line_items = OrderLineItem.objects.filter(order=self)
        return sum([order_line_item.rate * order_line_item.quantity for order_line_item in order_line_items])

    def get_order_type(self):
        # Assign variables comparing Order StartDate and EndDate to OrderGroup StartDate and EndDate.
        order_order_group_start_date_equal = self.start_date == self.order_group.start_date
        order_order_group_end_dates_equal = self.end_date == self.order_group.end_date

        # Does the OrderGroup have a Subscription?
        has_subscription = hasattr(self.order_group, 'subscription')

        # Are Order.StartDate and Order.EndDate equal?
        order_start_end_dates_equal = self.start_date == self.end_date

        # Orders in OrderGroup.
        order_count = Order.objects.filter(order_group=self.order_group).count() > 1

        # Assign variables based on Order.Type.
        # DELIVERY: Order.StartDate == OrderGroup.StartDate AND Order.StartDate == Order.EndDate 
        # AND Order.EndDate != OrderGroup.EndDate.
        order_type_delivery = order_order_group_start_date_equal and order_start_end_dates_equal and not order_order_group_end_dates_equal
        # ONE TIME: Order.StartDate == OrderGroup.StartDate AND Order.EndDate == OrderGroup.EndDate
        # AND OrderGroup has no Subscription.
        order_type_one_time = order_order_group_start_date_equal and order_order_group_end_dates_equal and not has_subscription
        # REMOVAL: Order.EndDate == OrderGroup.EndDate AND OrderGroup.Orders.Count > 1.
        order_type_removal = order_order_group_end_dates_equal and order_count > 1
        # SWAP: OrderGroup.Orders.Count > 1 AND Order.EndDate != OrderGroup.EndDate AND OrderGroup has no Subscription.
        order_type_swap = order_count > 1 and not order_order_group_end_dates_equal and not has_subscription
        # AUTO RENEWAL: OrderGroup has Subscription and does not meet any other criteria.
        order_type_auto_renewal = has_subscription and not order_type_delivery and not order_type_one_time and not order_type_removal and not order_type_swap

        if order_type_delivery:
            return Order.Type.DELIVERY
        elif order_type_one_time:
            return Order.Type.ONE_TIME
        elif order_type_removal:
            return Order.Type.REMOVAL
        elif order_type_swap:
            return Order.Type.SWAP
        elif order_type_auto_renewal:
            return Order.Type.AUTO_RENEWAL
        else:
            return None

    # def pre_save(sender, instance, *args, **kwargs):
    #     # Check if SubmittedOn has changed.
    #     print(instance.pk)
    #     old_submitted_on = Order.objects.get(pk=instance.pk).submitted_on if Order.objects.filter(pk=instance.pk).exists() else None
    #     instance.submitted_on_has_changed = old_submitted_on != instance.submitted_on

    def clean(self):
        # Ensure end_date is on or after start_date.
        if self.start_date > self.end_date:
            raise ValidationError('Start date must be on or before end date')
        # Ensure start_date is on or after OrderGroup start_date.
        elif self.start_date < self.order_group.start_date:
            raise ValidationError('Start date must be on or after OrderGroup start date')
        # Ensure end_date is on or before OrderGroup end_date.
        elif self.order_group.end_date and self.end_date > self.order_group.end_date:
            raise ValidationError('End date must be on or before OrderGroup end date')
        # Ensure service_date is between start_date and end_date.
        elif self.service_date < self.start_date or (self.order_group.end_date and self.service_date > self.end_date):
            raise ValidationError('Service date must be between start date and end date')
        # Ensure this Order doesn't overlap with any other Orders for this OrderGroup.
        elif Order.objects.filter(
            order_group=self.order_group,
            start_date__lt=self.end_date, 
            end_date__gt=self.start_date,
        ).exclude(id=self.id).exists():
            raise ValidationError('This Order overlaps with another Order for this OrderGroup')
        # Only 1 Order from an OrderGroup can be in the cart 
        # (Order.submittedDate == null) at a time.
        elif Order.objects.filter(
            order_group=self.order_group,
            submitted_on__isnull=True,
        ).exclude(id=self.id).exists():
            raise ValidationError('Only 1 Order from an OrderGroup can be in the cart at a time')
            
    def save(self, *args, **kwargs):
        self.clean()

        # Send email to internal team. Only on our PROD environment.
        if self.submitted_on != self.__original_submitted_on and self.submitted_on is not None:
            self.send_internal_order_confirmation_email()

        # Send email to customer if status has changed to "Scheduled".
        if self.status != self.__original_status and self.status == Order.SCHEDULED:
            self.send_customer_email_when_order_scheduled()

        return super(Order, self).save(*args, **kwargs)

    def pre_save(sender, instance, *args, **kwargs):
        # Check if "instance" is in the database yet.
        db_instance = Order.objects.filter(pk=instance.pk).first()
        if not db_instance:
            order_group_orders = Order.objects.filter(order_group=instance.order_group)
            if order_group_orders.count() == 0:
                instance.order_type = 'Delivery'
            elif instance.order_group.end_date == instance.end_date and order_group_orders.count() > 0:
                instance.order_type = 'Removal'
            else:
                instance.order_type = 'Swap'

    def post_save(sender, instance, created, **kwargs):
        order_line_items = OrderLineItem.objects.filter(order=instance)
        # if instance.submitted_on_has_changed and order_line_items.count() == 0:
        if created and order_line_items.count() == 0:
            try:
                # Create Delivery Fee OrderLineItem.
                order_group_orders = Order.objects.filter(order_group=instance.order_group)
                if order_group_orders.count() == 0:
                    OrderLineItem.objects.create(
                        order = instance,
                        order_line_item_type = OrderLineItemType.objects.get(code="DELIVERY"),
                        rate = instance.order_group.seller_product_seller_location.delivery_fee,
                        quantity = 1,
                        description = "Delivery Fee",
                        platform_fee_percent = instance.order_group.take_rate,
                        is_flat_rate = True,
                    )

                # Create Removal Fee OrderLineItem.
                if instance.order_group.end_date == instance.end_date and order_group_orders.count() > 1:
                    OrderLineItem.objects.create(
                        order = instance,
                        order_line_item_type = OrderLineItemType.objects.get(code="REMOVAL"),
                        rate = instance.order_group.seller_product_seller_location.removal_fee,
                        quantity = 1,
                        description = "Removal Fee",
                        platform_fee_percent = instance.order_group.take_rate,
                        is_flat_rate = True,
                    )
                    # Don't add any other OrderLineItems if this is a removal.
                    return

                # Create OrderLineItems for newly "submitted" order.
                # Service Price.
                if hasattr(instance.order_group, 'service'):
                    order_line_item_type = OrderLineItemType.objects.get(code="SERVICE")
                    OrderLineItem.objects.create(
                        order = instance,
                        order_line_item_type = order_line_item_type,
                        rate = instance.order_group.service.rate,
                        quantity = instance.order_group.service.miles or 1,
                        is_flat_rate = instance.order_group.service.miles is None,
                        platform_fee_percent = instance.order_group.take_rate,
                    )

                # Rental Price.
                if hasattr(instance.order_group, 'rental'):
                    day_count = (instance.end_date - instance.start_date).days if instance.end_date else 0
                    days_over_included = day_count - instance.order_group.rental.included_days
                    order_line_item_type = OrderLineItemType.objects.get(code="RENTAL")

                    # Create OrderLineItem for Included Days.
                    OrderLineItem.objects.create(
                        order = instance,
                        order_line_item_type = order_line_item_type,
                        rate = instance.order_group.rental.price_per_day_included,
                        quantity = instance.order_group.rental.included_days,
                        description = "Included Days",
                        platform_fee_percent = instance.order_group.take_rate,
                    )

                    # Create OrderLineItem for Additional Days.
                    if days_over_included > 0:
                        OrderLineItem.objects.create(
                            order = instance,
                            order_line_item_type = order_line_item_type,
                            rate = instance.order_group.rental.price_per_day_additional,
                            quantity = days_over_included,
                            description = "Additional Days",
                            platform_fee_percent = instance.order_group.take_rate,
                        )

                # Material Price.
                if hasattr(instance.order_group, 'material'):
                    tons_over_included = (instance.order_group.tonnage_quantity or 0) - instance.order_group.material.tonnage_included
                    order_line_item_type = OrderLineItemType.objects.get(code="MATERIAL")  

                    # Create OrderLineItem for Included Tons.   
                    OrderLineItem.objects.create(
                        order=instance,
                        order_line_item_type=order_line_item_type,
                        rate = instance.order_group.material.price_per_ton,
                        quantity = instance.order_group.material.tonnage_included,
                        description = "Included Tons",
                        platform_fee_percent = instance.order_group.take_rate,
                    )

                    # Create OrderLineItem for Additional Tons.
                    if tons_over_included > 0:
                        OrderLineItem.objects.create(
                            order=instance,
                            order_line_item_type=order_line_item_type,
                            rate=instance.order_group.material.price_per_ton,
                            quantity=tons_over_included,
                            description="Additional Tons",
                            platform_fee_percent = instance.order_group.take_rate,
                        )
            except Exception as e:
                print(e)
                pass

    def send_internal_order_confirmation_email(self):
        # Send email to internal team. Only on our PROD environment.
        if settings.ENVIRONMENT == "TEST":
            try:
                mailchimp.messages.send({"message": {
                    "headers": {
                        "reply-to": "dispatch@trydownstream.io",
                    },
                    "from_name": "Downstream",
                    "from_email": "dispatch@trydownstream.io",
                    "to": [{"email": "dispatch@trydownstream.io"}],
                    "subject": "Order Confirmed",
                    "track_opens": True,
                    "track_clicks": True,
                    "html": render_to_string(
                        'order-submission-email.html',
                        {
                            "orderId": self.id,
                            "seller": self.order_group.seller_product_seller_location.seller_location.seller.name,
                            "sellerLocation": self.order_group.seller_product_seller_location.seller_location.name,
                            "mainProduct": self.order_group.seller_product_seller_location.seller_product.product.main_product.name,
                            "bookingType": self.order_type,
                            "wasteType": self.order_group.waste_type.name,
                            "supplierTonsIncluded": self.order_group.material.tonnage_included,
                            "supplierRentalDaysIncluded": self.order_group.rental.included_days,
                            "serviceDate": self.end_date,
                            "timeWindow": self.schedule_window,
                            "locationAddress": self.order_group.user_address.street,
                            "locationCity": self.order_group.user_address.city,
                            "locationState": self.order_group.user_address.state,
                            "locationZip": self.order_group.user_address.postal_code,
                            "locationDetails": self.order_group.access_details,
                            "additionalDetails": self.order_group.placement_details,
                        }
                    ),
                }})
            except Exception as e:
                print("An exception occurred.")
                print(e)

    def send_customer_email_when_order_scheduled(self):
        # Send email to customer when order is scheduled. Only on our PROD environment.
        if settings.ENVIRONMENT == "TEST":
            try:
                auth0_user = get_user_data(self.order_group.user.user_id)

                try:
                    call_to_action_url = get_password_change_url(self.order_group.user.user_id) if not auth0_user['email_verified'] else "https://app.trydownstream.io/orders"
                except Exception as e:
                    call_to_action_url = "https://app.trydownstream.io/orders"

                mailchimp.messages.send({"message": {
                    "headers": {
                        "reply-to": "dispatch@trydownstream.io",
                    },
                    "from_name": "Downstream",
                    "from_email": "dispatch@trydownstream.io",
                    "to": [
                        {"email": self.order_group.user.email}, 
                        {"email": "thayes@trydownstream.io"}
                    ],
                    "subject": "Downstream | Order Confirmed | " + self.order_group.user_address.formatted_address(),
                    "track_opens": True,
                    "track_clicks": True,
                    "html": render_to_string(
                        'order-confirmed-email.html',
                        {
                            "orderId": self.id,
                            "booking_url": call_to_action_url,
                            "main_product": self.order_group.seller_product_seller_location.seller_product.product.main_product.name,
                            "waste_type": self.order_group.waste_type.name,
                            "included_tons": self.order_group.material.tonnage_included,
                            "included_rental_days": self.order_group.rental.included_days,
                            "service_date": self.end_date,
                            "location_address": self.order_group.user_address.street,
                            "location_city": self.order_group.user_address.city,
                            "location_state": self.order_group.user_address.state,
                            "location_zip": self.order_group.user_address.postal_code,
                            "location_details": self.order_group.access_details or "None",
                            "additional_details": self.order_group.placement_details or "None",
                        }
                    ),
                }})
            except Exception as e:
                print("An exception occurred.")
                print(e)


    def __str__(self):
        return self.order_group.seller_product_seller_location.seller_product.product.main_product.name + ' - ' + self.order_group.user_address.name
    
class OrderDisposalTicket(BaseModel):
    order = models.ForeignKey(Order, models.PROTECT)
    waste_type = models.ForeignKey(WasteType, models.PROTECT)
    disposal_location = models.ForeignKey(DisposalLocation, models.PROTECT)
    ticket_id = models.CharField(max_length=255)
    weight = models.DecimalField(max_digits=18, decimal_places=2)

    def __str__(self):
        return self.ticket_id + ' - ' + self.order.order_group.user_address.name
    
class OrderLineItemType(BaseModel):
    name = models.CharField(max_length=255)
    units = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    stripe_tax_code_id = models.CharField(max_length=255)

    def __str__(self):
        return self.name
    
class OrderLineItem(BaseModel):
    PERCENTAGE_VALIDATOR = [MinValueValidator(0), MaxValueValidator(1000)]

    order = models.ForeignKey(Order, models.CASCADE, related_name='order_line_items')
    order_line_item_type = models.ForeignKey(OrderLineItemType, models.PROTECT)
    rate = models.DecimalField(max_digits=18, decimal_places=2)
    quantity = models.DecimalField(max_digits=18, decimal_places=2)
    platform_fee_percent = models.DecimalField(max_digits=18, decimal_places=2, default=20, validators=PERCENTAGE_VALIDATOR)
    description = models.CharField(max_length=255, blank=True, null=True)
    is_flat_rate = models.BooleanField(default=False)
    stripe_invoice_line_item_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return str(self.order) + ' - ' + self.order_line_item_type.name
    
    def get_invoice(self):
        if self.stripe_invoice_line_item_id:
            invoice_line_item = stripe.InvoiceItem.retrieve(self.stripe_invoice_line_item_id)
            return stripe.Invoice.retrieve(invoice_line_item.invoice)
        else:
            return None

    def is_paid(self):
        invoice = self.get_invoice()
        if invoice and invoice.status != "draft":
            return invoice.status == "paid"
        else:
            # Return None if OrderLineItem is not associated with an Invoice or
            # Invoice is in draft status.
            return None
        
    def seller_payout_price(self):
        return round((self.rate or 0) * (self.quantity or 0), 2)
    
    def customer_price(self):
        seller_price = self.seller_payout_price()
        customer_price = seller_price * (1 + (self.platform_fee_percent / 100))
        return round(customer_price, 2)

class SellerInvoicePayable(BaseModel):
    STATUS_CHOICES = (
        ("UNPAID", "Unpaid"),
        ("ESCALATED", "Escalated"),
        ("ERROR", "Error"),
        ("READY_FOR_PAYOUT", "Ready for Payout"),
        ("PAID", "Paid"),
    )   

    def get_file_path(instance, filename):
        ext = filename.split('.')[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return filename

    seller_location = models.ForeignKey(SellerLocation, models.PROTECT)
    invoice_file = models.FileField(upload_to=get_file_path, blank=True, null=True)
    supplier_invoice_id = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="UNPAID")

    def auto_delete_file_on_delete(sender, instance, **kwargs):
        """
        Deletes file from filesystem
        when corresponding `Payout` object is deleted.
        """
        if instance.invoice_file:
            instance.invoice_file.delete(save=False)

    def auto_delete_file_on_change(sender, instance, **kwargs):
        """
        Deletes old file from filesystem
        when corresponding `Payout` object is updated
        with new file.
        """
        if not instance.pk:
            return False

        try:
            old_file = Payout.objects.get(pk=instance.pk).invoice_file
            print(old_file)
        except Payout.DoesNotExist:
            return False

        new_file = instance.invoice_file
        if not old_file == new_file:
            old_file.delete(save=False)

class SellerInvoicePayableLineItem(BaseModel):
    seller_invoice_payable = models.ForeignKey(SellerInvoicePayable, models.CASCADE, blank=True, null=True)
    order = models.ForeignKey(Order, models.CASCADE)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)

class Payout(BaseModel):
    order = models.ForeignKey(Order, models.CASCADE)
    checkbook_payout_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_transfer_id = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)

post_save.connect(UserGroup.post_create, sender=UserGroup)
# pre_save.connect(User.pre_create, sender=User)  
post_delete.connect(User.post_delete, sender=User)
pre_save.connect(UserAddress.pre_save, sender=UserAddress)
pre_save.connect(UserGroupBilling.pre_save, sender=UserGroupBilling)
pre_save.connect(Order.pre_save, sender=Order)
post_save.connect(Order.post_save, sender=Order)
pre_save.connect(SellerLocationMailingAddress.pre_save, sender=SellerLocationMailingAddress)
pre_save.connect(SellerLocation.pre_save, sender=SellerLocation)
post_save.connect(SellerProductSellerLocation.post_save, sender=SellerProductSellerLocation)
post_save.connect(SellerProductSellerLocationService.post_save, sender=SellerProductSellerLocationService)
post_save.connect(SellerProductSellerLocationMaterial.post_save, sender=SellerProductSellerLocationMaterial)
pre_save.connect(SellerInvoicePayable.auto_delete_file_on_change, sender=SellerInvoicePayable)
post_delete.connect(SellerInvoicePayable.auto_delete_file_on_delete, sender=SellerInvoicePayable)