import datetime
from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save, post_save
import uuid
import stripe
from simple_salesforce import Salesforce

from api.utils.auth0 import create_user, get_user_from_email

stripe.api_key = settings.STRIPE_SECRET_KEY

sf = Salesforce(
    username='thayes@trydownstream.io.stage', 
    password='LongLiveDownstream12!', 
    security_token='DSwuelzBBaTVRXSdtQwC7IE8', 
    domain='test'
)

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
       abstract = True

class Seller(BaseModel):
    MONDAY= 'Monday', 
    TUESDAY = 'Tuesday', 
    WEDNESDAY = 'Wednesday', 
    THURSDAY = 'Thursday', 
    FRIDAY = 'Friday', 
    SATURDAY = 'Saturday', 
    SUNDAY = 'Sunday'
 
    open_day_choices = (
       ('MONDAY', 'Monday'), 
       ('TUESDAY', 'Tuesday'), 
       ('WEDNESDAY', 'Wednesday'), 
       ('THURSDAY', 'Thursday'), 
       ('FRIDAY', 'Friday'), 
       ('SATURDAY', 'Saturday'), 
       ('SUNDAY', 'Sunday')
    )
        
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=40)
    website = models.URLField(blank=True, null=True)
    type = models.CharField(max_length=255, choices=[('Broker', 'Broker'), ('Compost facility', 'Compost facility'), ('Delivery', 'Delivery'), ('Equipment', 'Equipment'), ('Fencing', 'Fencing'), ('Industrial', 'Industrial'), ('Junk', 'Junk'), ('Landfill', 'Landfill'), ('Mover', 'Mover'), ('MRF', 'MRF'), ('Other recycler', 'Other recycler'), ('Paint recycler', 'Paint recycler'), ('Portable Storage', 'Portable Storage'), ('Portable Toilet', 'Portable Toilet'), ('Processor', 'Processor'), ('Roll-off', 'Roll-off'), ('Scrap yard', 'Scrap yard'), ('Tires', 'Tires')], blank=True, null=True)
    location_type = models.CharField(max_length=255, choices=[('Services', 'Services'), ('Disposal site', 'Disposal site')], blank=True, null=True)
    status = models.CharField(max_length=255, choices=[('Inactive', 'Inactive'), ('Inactive - Onboarding', 'Inactive - Onboarding'), ('Inactive - Pending approval', 'Inactive - Pending approval'), ('Active - under review', 'Active - under review'), ('Active', 'Active')], blank=True, null=True)
    lead_time = models.CharField(max_length=255, blank=True, null=True)
    type_display = models.CharField(max_length=255, choices=[('Landfill', 'Landfill'), ('MRF', 'MRF'), ('Industrial', 'Industrial'), ('Scrap yard', 'Scrap yard'), ('Compost facility', 'Compost facility'), ('Processor', 'Processor'), ('Paint recycler', 'Paint recycler'), ('Tires', 'Tires'), ('Other recycler', 'Other recycler'), ('Roll-off', 'Roll-off'), ('Mover', 'Mover'), ('Junk', 'Junk'), ('Delivery', 'Delivery'), ('Broker', 'Broker'), ('Equipment', 'Equipment')], blank=True, null=True)
    stripe_connect_id = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    marketplace_display_name = models.CharField(max_length=255, blank=True, null=True)
    open_days = models.CharField(max_length=255, choices = open_day_choices, blank=True, null=True)
    open_time = models.TimeField(blank=True, null=True)
    close_time = models.TimeField(blank=True, null=True)
    lead_time_hrs = models.DecimalField(max_digits=18, decimal_places=0)
    announcement = models.TextField(blank=True, null=True)
    live_menu_is_active = models.BooleanField(default=False)
    location_logo_url = models.URLField(blank=True, null=True)
    downstream_insurance_requirements_met = models.BooleanField(default=False)
    badge = models.CharField(max_length=255, choices=[('New', 'New'), ('Pro', 'Pro'), ('Platinum', 'Platinum')], blank=True, null=True)
    tire_recycler_cert_registration_id_co = models.CharField(max_length=100, blank=True, null=True)
    composting_classification = models.CharField(max_length=100, blank=True, null=True)
    max_paint_gallons_accepted = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    recycling_disposal_classification = models.CharField(max_length=100, blank=True, null=True)

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

    def __str__(self):
        return self.name

class UserGroup(BaseModel):
    name = models.CharField(max_length=255)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    pay_later = models.BooleanField(default=False)
    autopay= models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
    def post_create(sender, instance, created, **kwargs):
        if created:
            customer = stripe.Customer.create()
            instance.stripe_customer_id = customer.id
            instance.save()

class UserAddressType(BaseModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class UserAddress(BaseModel):
    user_group = models.ForeignKey(UserGroup, models.CASCADE, blank=True, null=True)
    user_address_type = models.ForeignKey(UserAddressType, models.CASCADE, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255)
    project_id = models.CharField(max_length=50, blank=True, null=True)
    street = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=80)
    latitude = models.DecimalField(max_digits=18, decimal_places=15)
    longitude = models.DecimalField(max_digits=18, decimal_places=15)
    autopay = models.BooleanField(default=False)


    def __str__(self):
        return self.name

class User(BaseModel):
    user_group = models.ForeignKey(UserGroup, models.CASCADE, blank=True, null=True)
    user_id = models.CharField(max_length=255, blank=True)
    mailchip_id = models.CharField(max_length=255, blank=True, null=True)
    intercom_id = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=40, blank=True, null=True)
    email = models.CharField(max_length=255)
    photo_url = models.URLField(blank=True, null=True)
    seller = models.ForeignKey(Seller, models.DO_NOTHING, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    device_token= models.CharField(max_length=255, blank=True, null=True)
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.email
    
    def post_create(sender, instance, created, **kwargs):
        if created:
            # Create stripe customer.
            try:
                print('creating stripe customer')
                customer = stripe.Customer.create()
                instance.stripe_customer_id = customer.id
            except Exception as e:
                pass
                
            
            # Create or attach to Auth0 user (only on Stage).
            print('creating or attaching to auth0 user')
            user_id = get_user_from_email(instance.email)
            if user_id:
                print('auth0 user exists')
                # User already exists in Auth0.
                instance.user_id = user_id
            else:
                print('auth0 user does not exist')
                # Create user in Auth0.
                instance.user_id = create_user(instance.email)
            instance.save()

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
    
class UserSellerReview(BaseModel): #added this model 2/25/2023 by Dylan
    seller = models.ForeignKey(Seller, models.DO_NOTHING, related_name='user_seller_review')
    user = models.ForeignKey(User, models.DO_NOTHING, related_name='user_seller_review')
    rating = models.IntegerField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f'{self.seller.name} - {self.rating if self.rating else ""}'

class MainProductCategory(BaseModel):
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True, null=True)
    image = models.TextField(blank=True, null=True)
    icon = models.TextField(blank=True, null=True)
    sort = models.DecimalField(max_digits=18, decimal_places=0)
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
    cubic_yards = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    ar_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image_del = models.TextField(blank=True, null=True)
    main_product_category = models.ForeignKey(MainProductCategory, models.CASCADE)
    sort = models.DecimalField(max_digits=18, decimal_places=0)
    included_tonnage_quantity = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    price_per_additional_ton = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    max_tonnage_quantity = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    max_rate = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    included_rate_quantity = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    main_product_code = models.CharField(max_length=255, blank=True, null=True) 
    
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

class Product(BaseModel):
    product_code = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    main_product = models.ForeignKey(MainProduct, models.CASCADE)
    removal_price = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f'{self.main_product.name} - {self.product_code}'

class SellerProduct(BaseModel):
    product = models.ForeignKey(Product, models.CASCADE, blank=True, null=True, related_name='seller_products')
    seller = models.ForeignKey(Seller, models.CASCADE, blank=True, null=True, related_name='seller_products')
   
    def __str__(self):
        return self.product.main_product.name + ' - ' + (self.product.product_code or "") + ' - ' + self.seller.name

class SellerProductSellerLocation(BaseModel):
    seller_product = models.ForeignKey(SellerProduct, models.CASCADE, blank=True, null=True, related_name='seller_location_seller_product')
    seller_location = models.ForeignKey(SellerLocation, models.CASCADE, blank=True, null=True, related_name='seller_location_seller_product')
    rate = models.DecimalField(max_digits=18, decimal_places=2)
    total_inventory = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True) # Added 2/20/2023 Total Quantity input by seller of product offered

    def __str__(self):
        return f'{self.seller_location.seller.name} - {self.seller_location.name} - {self.seller_product.product.main_product.name}'
    
class Subscription(BaseModel): #Added 2/20/23
    subscription_number = models.CharField(max_length=255) #Added 2/20/2023. May not need this, but thought this could be user facing if needed instead of a long UUID column so that the customer could reference this in communitcation with us if needed.
    interval_days = models.IntegerField(blank=True, null=True) #Added 2/20/2023. Number of Days from dropoff to pickup for each subscription order.
    length_days = models.IntegerField(blank=True, null=True) #6.6.23
    subscription_type = models.CharField(max_length=35, choices=[('On demand without subscription', 'On demand without subscription'), ('On demand with subscription', 'On demand with subscription'), ('Auto scheduled with subscription','Auto scheduled with subscription')], blank=True, null=True) #6.6.23


class OrderGroup(BaseModel):
    user = models.ForeignKey(User, models.PROTECT)
    user_address = models.ForeignKey(UserAddress, models.PROTECT)
    seller_product_seller_location = models.ForeignKey(SellerProductSellerLocation, models.PROTECT)
    subscription = models.ForeignKey(Subscription, models.PROTECT, blank=True, null=True)

    def __str__(self):
        return str(self.id)

class ProductAddOnChoice(BaseModel):
    name = models.CharField(max_length=80)
    product = models.ForeignKey(Product, models.CASCADE)
    add_on_choice = models.ForeignKey(AddOnChoice, models.CASCADE)

    def __str__(self):
        return f'{self.product.main_product.name} - {self.add_on_choice.add_on.name} - {self.add_on_choice.name}'

class WasteType(BaseModel):
    name = models.CharField(max_length=80)

    def __str__(self):
        return self.name

class MainProductWasteType(BaseModel):
    waste_type = models.ForeignKey(WasteType, models.CASCADE)
    main_product = models.ForeignKey(MainProduct, models.CASCADE)

    def __str__(self):
        return f'{self.main_product.name} - {self.waste_type.name}'

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

    order_group = models.ForeignKey(OrderGroup, models.PROTECT)
    waste_type = models.ForeignKey(WasteType, models.DO_NOTHING, blank=True, null=True)
    disposal_location = models.ForeignKey(DisposalLocation, models.DO_NOTHING, blank=True, null=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    salesforce_order_id = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    service_date = models.DateField(blank=True, null=True) #6.6.23
    schedule_details = models.TextField(blank=True, null=True) #6.6.23 (Modified name to schedule_details from additional_schedule_details)
    access_details = models.TextField(blank=True, null=True)
    placement_details = models.TextField(blank=True, null=True) #6.6.23
    price = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    order_type =  models.CharField(max_length=255, choices=[('Automatic Renewal', 'Automatic Renewal'), ('Swap', 'Swap'),('Empty and Return','Empty and Return'),('Trip Charge/Dry Run','Trip Charge/Dry Run'),('Removal','Removal'),('On Demand','On Demand'),('Other','Other')], blank=True, null=True) #6.6.23
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

    def pre_create(sender, instance, *args, **kwargs):
        if Order.objects.filter(pk=instance.pk).count() == 0: 
            order = sf.Order.create({
                "order_type__c": "Delivery",
                "accountId": "0014x00001RgLBMAA3",
                "status": "Waiting for Request",
                "Rental_Start_Date__c": instance.start_date.strftime('%Y-%m-%d'),
                "Service_Date__c": instance.start_date.strftime('%Y-%m-%d'),
                "Rental_End_Date__c": instance.end_date.strftime('%Y-%m-%d'),
                "effectiveDate": instance.start_date.strftime('%Y-%m-%d'),
                "Access_Details__c": instance.access_details,
                "schedule_details__c": instance.schedule_details,
                "description": "User: " + (instance.order_group.user.email if instance.order_group.user else "None") + " | User Address: " + (instance.order_group.user_address.name if instance.order_group.user_address else "None") + " " + (instance.order_group.user_address.street if instance.order_group.user_address else "None")  + " " + (instance.order_group.user_address.city if instance.order_group.user_address else "None")  + " " + (instance.order_group.user_address.state if instance.order_group.user_address else "None") + " " + (instance.order_group.user_address.postal_code if instance.order_group.user_address else "None") + " | Waste Type: " + (instance.waste_type.name if instance.waste_type else "None")  + " | Disposal Location: " + (instance.disposal_location.name if instance.disposal_location else "None")  + " | Price: " + (str(instance.price) if instance.price else "None") + " | Main Product: " + (instance.order_group.seller_product_seller_location.seller_product.product.main_product.name if instance.order_group.seller_product_seller_location else "None") + " - " + (instance.order_group.seller_product_seller_location.seller_location.name if instance.order_group.seller_product_seller_location else "None") + " | Seller: " + (instance.order_group.seller_product_seller_location.seller_location.seller.name if instance.order_group.seller_product_seller_location else "None") + " | Seller Location: " + (instance.order_group.seller_product_seller_location.seller_location.name if instance.order_group.seller_product_seller_location else "None"),
            })
            instance.salesforce_order_id = order['id']

    def post_update(sender, instance, created, **kwargs):
        if not created:
            sf.Order.update(
                instance.salesforce_order_id,
                {
                    "Access_Details__c": instance.access_details,
                    "schedule_details__c": instance.schedule_details,
                }
            )
            instance.save()

    def __str__(self):
        return self.order_group.seller_product_seller_location.seller_product.product.main_product.name + ' - ' + self.order_group.user_address.name

class OrderDisposalTicket(BaseModel):
    order = models.ForeignKey(Order, models.PROTECT)
    waste_type = models.ForeignKey(WasteType, models.PROTECT)
    disposal_location = models.ForeignKey(DisposalLocation, models.PROTECT)
    ticket_id = models.CharField(max_length=255)
    weight = models.DecimalField(max_digits=18, decimal_places=2)

    def __str__(self):
        return self.ticket_id + ' - ' + self.order.user_address.name
    
post_save.connect(UserGroup.post_create, sender=UserGroup)
post_save.connect(User.post_create, sender=User)  
pre_save.connect(Order.pre_create, sender=Order)
# post_save.connect(Order.post_update, sender=Order)