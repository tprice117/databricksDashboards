from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
import uuid
import stripe

from api.utils import get_price_for_seller

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
      [('Monday', 'Monday'), 
       ('Tuesday', 'Tuesday'), 
       ('Wednesday', 'Wednesday'), 
       ('Thursday', 'Thursday'), 
       ('Friday', 'Friday'), 
       ('Saturday', 'Saturday'), 
       ('Sunday', 'Sunday')]
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
    open_days = models.CharField(max_length=4099, choices = open_day_choices, blank=True, null=True)
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
    seller = models.ForeignKey(Seller, models.DO_NOTHING)
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
    
class UserAddress(BaseModel):
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

class User(BaseModel):
    user_id = models.CharField(max_length=255)
    phone = models.CharField(max_length=40, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    photo_url = models.URLField(blank=True, null=True)
    seller = models.ForeignKey(Seller, models.DO_NOTHING, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    device_token= models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.email
    
    def post_create(sender, instance, created, **kwargs):
        if created:
            customer = stripe.Customer.create()
            instance.stripe_customer_id = customer.id
            instance.save()

class UserUserAddress(BaseModel):
    user = models.ForeignKey(User, models.DO_NOTHING)
    user_address = models.ForeignKey(UserAddress, models.DO_NOTHING)

    def __str__(self):
        return f'{self.user.email} - {self.user_address.street}'
    
class UserSellerReview(BaseModel): #added this model 2/25/2023 by Dylan
    seller = models.ForeignKey(Seller, models.DO_NOTHING, related_name='user_seller_review')
    user = models.ForeignKey(User, models.DO_NOTHING, related_name='user_seller_review')
    rating = models.IntegerField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class AddOn(BaseModel):
    name = models.CharField(max_length=80)
    sort = models.DecimalField(max_digits=18, decimal_places=0)

    def __str__(self):
        return self.name

class AddOnChoice(BaseModel):
    name = models.CharField(max_length=80)
    add_on = models.ForeignKey(AddOn, models.DO_NOTHING)

    def __str__(self):
        return f'{self.add_on.name} - {self.name}'

class MainProductCategory(BaseModel):
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True, null=True)
    image = models.TextField(blank=True, null=True)
    icon = models.TextField(blank=True, null=True)
    sort = models.DecimalField(max_digits=18, decimal_places=0)

    def __str__(self):
        return self.name

class MainProductCategoryInfo(BaseModel):
    name = models.CharField(max_length=80)
    main_product_category = models.ForeignKey(MainProductCategory, models.DO_NOTHING)

    def __str__(self):
        return self.name

class MainProduct(BaseModel):
    name = models.CharField(max_length=80)
    cubic_yards = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    ar_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image_del = models.TextField(blank=True, null=True)
    main_product_category = models.ForeignKey(MainProductCategory, models.DO_NOTHING)
    sort = models.DecimalField(max_digits=18, decimal_places=0)
    included_tonnage_quantity = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    price_per_additional_ton = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    max_tonnage_quantity = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    max_rate = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    included_rate_quantity = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    
    def __str__(self):
        return self.name

class MainProductInfo(BaseModel):
    name = models.CharField(max_length=80)
    main_product = models.ForeignKey(MainProduct, models.DO_NOTHING)

    def __str__(self):
        return self.name

class MainProductAddOn(BaseModel):
    main_product = models.ForeignKey(MainProduct, models.DO_NOTHING)
    add_on = models.ForeignKey(AddOn, models.DO_NOTHING)

    def __str__(self):
        return f'{self.main_product.name} - {self.add_on.name}'

class Product(BaseModel):
    product_code = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    main_product = models.ForeignKey(MainProduct, models.DO_NOTHING)

    def __str__(self):
        return self.main_product.name if self.main_product and self.main_product.name else str(self.id)

class SellerProduct(BaseModel):
    product = models.ForeignKey(Product, models.DO_NOTHING, blank=True, null=True, related_name='seller_products')
    seller = models.ForeignKey(Seller, models.DO_NOTHING, blank=True, null=True, related_name='seller_products')
   
    def __str__(self):
        return (self.product.main_product.name if self.product and self.product.main_product else '') + ' - ' + self.seller.name

class SellerProductSellerLocation(BaseModel):
    seller_product = models.ForeignKey(SellerProduct, models.DO_NOTHING, blank=True, null=True, related_name='seller_location_seller_product')
    seller_location = models.ForeignKey(SellerLocation, models.DO_NOTHING, blank=True, null=True, related_name='seller_location_seller_product')
    rate = models.DecimalField(max_digits=18, decimal_places=2)
    total_inventory = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True) # Added 2/20/2023 Total Quantity input by seller of product offered

    def __str__(self):
        return f'{self.seller_location.seller.name} - {self.seller_location.name} - {self.seller_product.product.main_product.name}'
    
class Subscription(BaseModel): #Added 2/20/23
    subscription_number = models.CharField(max_length=255) #Added 2/20/2023. May not need this, but thought this could be user facing if needed instead of a long UUID column so that the customer could reference this in communitcation with us if needed.
    interval_days = models.IntegerField(blank=True, null=True) #Added 2/20/2023. Number of Days from dropoff to pickup for each subscription order.

class OrderGroup(BaseModel):
    def __str__(self):
        return str(self.id)

class ProductAddOnChoice(BaseModel):
    name = models.CharField(max_length=80)
    product = models.ForeignKey(Product, models.DO_NOTHING)
    add_on_choice = models.ForeignKey(AddOnChoice, models.DO_NOTHING)

    def __str__(self):
        return self.name

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
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    user_address = models.ForeignKey(UserAddress, models.DO_NOTHING, blank=True, null=True)
    subscription = models.ForeignKey(Subscription, models.DO_NOTHING, blank=True, null=True)
    order_group = models.ForeignKey(OrderGroup, models.DO_NOTHING, blank=True, null=True)
    waste_type = models.ForeignKey(WasteType, models.DO_NOTHING, blank=True, null=True)
    disposal_location = models.ForeignKey(DisposalLocation, models.DO_NOTHING, blank=True, null=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    additional_schedule_details = models.TextField(blank=True, null=True)
    access_details = models.TextField(blank=True, null=True)
    seller_product_seller_location = models.ForeignKey(SellerProductSellerLocation, models.DO_NOTHING, blank=True, null=True) #Added 2/25/2023 to create relationship between ordersdetail and sellerproductsellerlocation so that inventory can be removed from sellerproductsellerlocation inventory based on open orders.

    def post_create(sender, instance, created, **kwargs):
        if created:
            disposal_locations = DisposalLocation.objects.all()
            price = get_price_for_seller(
                instance.seller_product_seller_location, 
                instance.user_address.latitude, 
                instance.user_address.longitude,
                instance.waste_type.id, 
                instance.start_date, 
                instance.end_date, 
                disposal_locations
            )

            for item in price['line_items']:
                stripe.InvoiceItem.create(
                    customer=instance.user.stripe_customer_id,
                    amount=round(item['price']*100),
                    description=item['name'],
                    currency="usd",
                )
            invoice = stripe.Invoice.create(customer=instance.user.stripe_customer_id)
            instance.stripe_invoice_id = invoice.id
            instance.save()

    def __str__(self):
        return self.seller_product_seller_location.seller_product.product.main_product.name + ' - ' + self.user_address.name

post_save.connect(User.post_create, sender=User)  
post_save.connect(Order.post_create, sender=Order)
