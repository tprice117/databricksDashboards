from django.db import models
import uuid

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
       abstract = True

class Seller(BaseModel):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=40, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    type = models.CharField(max_length=255, choices=[('Landfill', 'Landfill'), ('MRF', 'MRF'), ('Industrial', 'Industrial'), ('Scrap yard', 'Scrap yard'), ('Compost facility', 'Compost facility'), ('Processor', 'Processor'), ('Paint recycler', 'Paint recycler'), ('Tires', 'Tires'), ('Other recycler', 'Other recycler'), ('Roll-off', 'Roll-off'), ('Mover', 'Mover'), ('Junk', 'Junk'), ('Delivery', 'Delivery'), ('Broker', 'Broker'), ('Equipment', 'Equipment')], blank=True, null=True)
    location_type = models.CharField(max_length=255, choices=[('Services', 'Services'), ('Disposal site', 'Disposal site')], blank=True, null=True)
    status = models.CharField(max_length=255, choices=[('Inactive', 'Inactive'), ('Inactive - Onboarding', 'Inactive - Onboarding'), ('Inactive - Pending approval', 'Inactive - Pending approval'), ('Active - under review', 'Active - under review'), ('Active', 'Active')], blank=True, null=True)
    lead_time = models.CharField(max_length=255, blank=True, null=True)
    type_display = models.CharField(max_length=255, choices=[('Landfill', 'Landfill'), ('MRF', 'MRF'), ('Industrial', 'Industrial'), ('Scrap yard', 'Scrap yard'), ('Compost facility', 'Compost facility'), ('Processor', 'Processor'), ('Paint recycler', 'Paint recycler'), ('Tires', 'Tires'), ('Other recycler', 'Other recycler'), ('Roll-off', 'Roll-off'), ('Mover', 'Mover'), ('Junk', 'Junk'), ('Delivery', 'Delivery'), ('Broker', 'Broker'), ('Equipment', 'Equipment')], blank=True, null=True)
    stripe_connect_id = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    marketplace_display_name = models.CharField(max_length=20, blank=True, null=True)
    open_days = models.CharField(max_length=4099, choices=[('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'), ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'), ('Sunday', 'Sunday')], blank=True, null=True)
    open_time = models.TimeField(blank=True, null=True)
    close_time = models.TimeField(blank=True, null=True)
    lead_time_hrs = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    announcement = models.TextField(blank=True, null=True)
    live_menu_is_active = models.BooleanField(default=False)
    location_logo_url = models.URLField(blank=True, null=True)
    downstream_insurance_requirements_met = models.BooleanField(default=False)
    badge = models.CharField(max_length=255, choices=[('New', 'New'), ('Pro', 'Pro'), ('Platinum', 'Platinum')], blank=True, null=True)
    average_rating = models.DecimalField(max_digits=2, decimal_places=1, blank=True, null=True)
    tire_recycler_cert_registration_id_co = models.CharField(max_length=100, blank=True, null=True)
    composting_classification = models.CharField(max_length=100, blank=True, null=True)
    max_paint_gallons_accepted = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    recycling_disposal_classification = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

class SellerLocation(BaseModel):
    seller = models.ForeignKey(Seller, models.DO_NOTHING, blank=True, null=True)
    name = models.CharField(max_length=255)
    street = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=40, blank=True, null=True)
    state = models.CharField(max_length=80, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=80, blank=True, null=True)
    latitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True, null=True)
    longitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True, null=True)

    def __str__(self):
        return self.name
    
class UserAddress(BaseModel):
    name = models.CharField(max_length=255)
    street = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=40, blank=True, null=True)
    state = models.CharField(max_length=80, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=80, blank=True, null=True)
    latitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True, null=True)
    longitude = models.DecimalField(max_digits=18, decimal_places=15, blank=True, null=True)

    def __str__(self):
        return self.name

class User(BaseModel):
    user_id = models.CharField(max_length=255)
    addresses = models.ManyToManyField(UserAddress, related_name='users')
    phone = models.CharField(max_length=40, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    photo_url = models.URLField(blank=True, null=True)
    seller = models.ForeignKey(Seller, models.DO_NOTHING, blank=True, null=True)
    stripe_customer_id = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)

    def __str__(self):
        return self.email
    
class UserSellerReview(models.Model): #added this model 2/25/2023 by Dylan
    seller = models.ForeignKey(Seller, models.DO_NOTHING, related_name='user_seller_review')
    user = models.ForeignKey(User, models.DO_NOTHING, related_name='user_seller_review')
    rating = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f'{self.user.id} - {self.seller.name}'

class AddOn(BaseModel):
    name = models.CharField(max_length=80, blank=True, null=True)
    sort = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)

    def __str__(self):
        return self.name

class AddOnChoice(BaseModel):
    name = models.CharField(max_length=80, blank=True, null=True)
    add_on = models.ForeignKey(AddOn, models.DO_NOTHING, blank=True, null=True)

    def __str__(self):
        return self.name

class MainProductCategory(BaseModel):
    name = models.CharField(max_length=80, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image = models.TextField(blank=True, null=True)
    icon = models.TextField(blank=True, null=True)
    sort = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)

    def __str__(self):
        return self.name

class MainProductCategoryInfo(BaseModel):
    name = models.CharField(max_length=80, blank=True, null=True)
    main_product_category = models.ForeignKey(MainProductCategory, models.DO_NOTHING, blank=True, null=True)

    def __str__(self):
        return self.name

class MainProduct(BaseModel):
    name = models.CharField(max_length=80, blank=True, null=True)
    cubic_yards = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    ar_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image_del = models.TextField(blank=True, null=True)
    main_product_category = models.ForeignKey(MainProductCategory, models.DO_NOTHING, blank=True, null=True)
    sort = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    included_tonnage_quantity = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    price_per_additional_ton = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    max_tonnage_quantity = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    max_rate = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    included_rate_quantity = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    
    def __str__(self):
        return self.name

class MainProductInfo(BaseModel):
    name = models.CharField(max_length=80, blank=True, null=True)
    main_product = models.ForeignKey(MainProduct, models.DO_NOTHING, blank=True, null=True)

    def __str__(self):
        return self.name

class MainProductAddOn(BaseModel):
    name = models.CharField(max_length=80, blank=True, null=True)
    main_product = models.ForeignKey(MainProduct, models.DO_NOTHING, blank=True, null=True)
    add_on = models.ForeignKey(AddOn, models.DO_NOTHING, blank=True, null=True)

    def __str__(self):
        return self.name

class Product(BaseModel):
    product_code = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    main_product = models.ForeignKey(MainProduct, models.DO_NOTHING, blank=True, null=True)

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
    rate = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    total_inventory = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True) # Added 2/20/2023 Total Quantity input by seller of product offered

class Subscription(BaseModel): #Added 2/20/23
    subscription_number = models.CharField(max_length=255) #Added 2/20/2023. May not need this, but thought this could be user facing if needed instead of a long UUID column so that the customer could reference this in communitcation with us if needed.
    interval_days = models.IntegerField(blank=True, null=True) #Added 2/20/2023. Number of Days from dropoff to pickup for each subscription order.

class Order(BaseModel):    
    def __str__(self):
        return self.seller.name + ' - ' + self.product.main_product.name

class OrderDetails(BaseModel):
    user_address = models.ForeignKey(UserAddress, models.DO_NOTHING, blank=True, null=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    time_slot = models.CharField(max_length=255, choices=[('4am-8am', '4am-8am'), ('8am-12pm', '8am-12pm'), ('12pm-4pm', '12pm-4pm'), ('4pm-8pm', '4pm-8pm'), ('8pm-12am', '8pm-12am')], blank=True, null=True)
    schedule_date = models.DateField(blank=True, null=True)
    additional_schedule_details = models.TextField(blank=True, null=True)
    access_details = models.TextField(blank=True, null=True)
    subscription = models.ForeignKey(Subscription, models.DO_NOTHING, blank=True, null=True) #Added 2/20/2023.
    order = models.ForeignKey(Order, models.DO_NOTHING, blank=True, null=True)
    seller_product_seller_location = models.ForeignKey(SellerProductSellerLocation, models.DO_NOTHING, blank=True, null=True) #Added 2/25/2023 to create relationship between ordersdetail and sellerproductsellerlocation so that inventory can be removed from sellerproductsellerlocation inventory based on open orders.

class OrderDetailsLineItem(BaseModel):
    order_details = models.ForeignKey(OrderDetails, models.DO_NOTHING, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    stripe_invoice_line_item_id = models.CharField(max_length=255, blank=True, null=True)

class ProductAddOnChoice(BaseModel):
    name = models.CharField(max_length=80, blank=True, null=True)
    product = models.ForeignKey(Product, models.DO_NOTHING, blank=True, null=True)
    add_on_choice = models.ForeignKey(AddOnChoice, models.DO_NOTHING, blank=True, null=True)

    def __str__(self):
        return self.name

class WasteType(BaseModel):
    name = models.CharField(max_length=80, blank=True, null=True)

    def __str__(self):
        return self.name

class MainProductWasteType(BaseModel):
    waste_type = models.ForeignKey(WasteType, models.DO_NOTHING, blank=True, null=True)
    main_product = models.ForeignKey(MainProduct, models.DO_NOTHING, blank=True, null=True)