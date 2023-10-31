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
from api.utils.auth0 import create_user, get_user_from_email, delete_user
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

stripe.api_key = settings.STRIPE_SECRET_KEY

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
    seller = models.ForeignKey(Seller, models.CASCADE)
    name = models.CharField(max_length=255)
    street = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=80)
    latitude = models.DecimalField(max_digits=18, decimal_places=15)
    longitude = models.DecimalField(max_digits=18, decimal_places=15)
    stripe_connect_account_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

class UserGroup(BaseModel):
    seller = models.ForeignKey(Seller, models.DO_NOTHING, blank=True, null=True)
    name = models.CharField(max_length=255)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    pay_later = models.BooleanField(default=False)
    autopay= models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    share_code = models.CharField(max_length=6, blank=True)
    parent_account_id = models.CharField(max_length=255, blank=True, null=True)

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
            else:
                # Create user in Auth0.
                self.user_id = create_user(self.email)

            # Send email to internal team. Only on our PROD environment.
            if settings.ENVIRONMENT == "TEST":
                try:
                    mailchimp = MailchimpTransactional.Client("md-U2XLzaCVVE24xw3tMYOw9w")
                    mailchimp.messages.send({"message": {
                        "headers": {
                            "reply-to": self.email,
                        },
                        "from_name": "Downstream",
                        "from_email": "noreply@trydownstream.io",
                        "to": [{"email": "support@trydownstream.io"}],
                        "subject": "New User App Signup",
                        "track_opens": True,
                        "track_clicks": True,
                        "text": "Woohoo! A new user signed up for the app. The email on their account is:" + self.email,
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
        return self.name
    
    def pre_save(sender, instance, *args, **kwargs):
        latitude, longitude = geocode_address(f"{instance.street} {instance.city} {instance.state} {instance.postal_code}")
        instance.latitude = latitude or 0
        instance.longitude = longitude or 0

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
    seller_product = models.ForeignKey(SellerProduct, models.CASCADE, related_name='seller_location_seller_product')
    seller_location = models.ForeignKey(SellerLocation, models.CASCADE, related_name='seller_location_seller_product')
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
        models.PROTECT
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
    product = models.ForeignKey(Product, models.CASCADE)
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

    def customer_price(self):
        order_line_items = OrderLineItem.objects.filter(order=self)
        return sum([order_line_item.rate * order_line_item.quantity for order_line_item in order_line_items])
    
    def seller_price(self):
        order_line_items = OrderLineItem.objects.filter(order=self)
        return sum([order_line_item.rate * order_line_item.quantity * (1 - (order_line_item.platform_fee_percent / 100)) for order_line_item in order_line_items])

    def pre_save(sender, instance, *args, **kwargs):
        # Check if SubmittedOn has changed.
        print(instance.pk)
        old_submitted_on = Order.objects.get(pk=instance.pk).submitted_on if Order.objects.filter(pk=instance.pk).exists() else None
        instance.submitted_on_has_changed = old_submitted_on != instance.submitted_on

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
        return super(Order, self).save(*args, **kwargs)

    def post_save(sender, instance, created, **kwargs):
        print("post_save")
        print(instance.submitted_on_has_changed)
        order_line_items = OrderLineItem.objects.filter(order=instance)
        # if instance.submitted_on_has_changed and order_line_items.count() == 0:
        if created and order_line_items.count() == 0:
            try:
                print("submitted_on_has_changed")
                main_product = instance.order_group.seller_product_seller_location.seller_product.product.main_product

                # Create OrderLineItems for newly "submitted" order.
                # Service Price.
                if instance.order_group.hasattr('service'):
                    order_line_item_type = OrderLineItemType.objects.get(code="SERVICE")
                    OrderLineItem.objects.create(
                        order = instance,
                        order_line_item_type = order_line_item_type,
                        rate = instance.order_group.service.rate,
                        quantity = instance.order_group.service.miles or 0,
                        is_flat_rate = instance.order_group.service.miles is None,
                    )
                # Rental Price.
                if instance.order_group.hasattr('rental'):
                    day_count = (instance.end_date - instance.start_date).days if instance.end_date else 0
                    days_over_included = day_count - instance.order_group.rental.included_days
                    order_line_item_type = OrderLineItemType.objects.get(code="RENTAL")

                    # Create OrderLineItem for Included Days.
                    OrderLineItem.objects.create(
                        order = instance,
                        order_line_item_type = order_line_item_type,
                        rate = instance.order_group.rental.price_per_day_included,
                        quantity = instance.order_group.rental.days_included,
                        description = "Included Days",
                    )

                    # Create OrderLineItem for Additional Days.
                    if days_over_included > 0:
                        OrderLineItem.objects.create(
                            order = instance,
                            order_line_item_type = order_line_item_type,
                            rate = instance.order_group.rental.price_per_day_additional,
                            quantity = days_over_included,
                            description = "Additional Days",
                        )
                # Material Price.
                if instance.order_group.hasattr('material'):
                    tons_over_included = (instance.order_group.tonnage_quantity or 0) - instance.order_group.material.tonnage_included
                    order_line_item_type = OrderLineItemType.objects.get(code="MATERIAL")  

                    # Create OrderLineItem for Included Tons.   
                    OrderLineItem.objects.create(
                        order=instance,
                        order_line_item_type=order_line_item_type,
                        rate = instance.order_group.material.price_per_ton,
                        quantity = instance.order_group.material.tonnage_included,
                        description = "Included Tons",
                    )

                    # Create OrderLineItem for Additional Tons.
                    if tons_over_included > 0:
                        OrderLineItem.objects.create(
                            order=instance,
                            order_line_item_type=order_line_item_type,
                            rate=instance.order_group.material.price_per_ton,
                            quantity=tons_over_included,
                            description="Additional Tons",
                        )
            except Exception as e:
                print(e)
                pass


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
    units = models.CharField(max_length=255, blank=True, null=True)
    code = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name
    
class OrderLineItem(BaseModel):
    PERCENTAGE_VALIDATOR = [MinValueValidator(0), MaxValueValidator(100)]

    order = models.ForeignKey(Order, models.CASCADE, related_name='order_line_items')
    order_line_item_type = models.ForeignKey(OrderLineItemType, models.PROTECT)
    rate = models.DecimalField(max_digits=18, decimal_places=2)
    quantity = models.DecimalField(max_digits=18, decimal_places=2)
    platform_fee_percent = models.DecimalField(max_digits=18, decimal_places=2, default=20, validators=PERCENTAGE_VALIDATOR)
    description = models.CharField(max_length=255, blank=True, null=True)
    is_flat_rate = models.BooleanField(default=False)

    def __str__(self):
        return str(self.order) + ' - ' + self.order_line_item_type.name

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
    melio_payout_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_transfer_id = models.CharField(max_length=255, blank=True, null=True)

class PayoutLineItem(BaseModel):
    payout = models.ForeignKey(Payout, models.CASCADE, related_name="payout_line_items")
    order = models.ForeignKey(Order, models.CASCADE)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)

class Payment(BaseModel):
    user_address = models.ForeignKey(UserAddress, models.PROTECT)
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)

    def total(self):
        total_invoiced = 0
        total_paid = 0
        for payment_line_item in self.payment_line_items.all():
            invoiced, paid = payment_line_item.amount()
            total_invoiced += invoiced
            total_paid += paid
        return total_invoiced, total_paid

class PaymentLineItem(BaseModel):
    payment = models.ForeignKey(Payment, models.CASCADE, related_name="payment_line_items")
    order = models.ForeignKey(Order, models.CASCADE)
    stripe_invoice_line_item_id = models.CharField(max_length=255, blank=True, null=True)

    def amount(self):
        if self.stripe_invoice_line_item_id:
            invoice = stripe.Invoice.retrieve(self.payment.stripe_invoice_id)
            invoice_line_item = stripe.InvoiceItem.retrieve(self.stripe_invoice_line_item_id)
            amount = invoice_line_item.amount / 100
            return amount, amount if invoice.status == "paid" else 0
        else:
            return None, None

post_save.connect(UserGroup.post_create, sender=UserGroup)
# pre_save.connect(User.pre_create, sender=User)  
post_delete.connect(User.post_delete, sender=User)
pre_save.connect(UserAddress.pre_save, sender=UserAddress)
pre_save.connect(Order.pre_save, sender=Order)
post_save.connect(Order.post_save, sender=Order)
post_save.connect(SellerProductSellerLocation.post_save, sender=SellerProductSellerLocation)
post_save.connect(SellerProductSellerLocationService.post_save, sender=SellerProductSellerLocationService)
post_save.connect(SellerProductSellerLocationMaterial.post_save, sender=SellerProductSellerLocationMaterial)
pre_save.connect(SellerInvoicePayable.auto_delete_file_on_change, sender=SellerInvoicePayable)
post_delete.connect(SellerInvoicePayable.auto_delete_file_on_delete, sender=SellerInvoicePayable)