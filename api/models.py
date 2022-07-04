# from django.db import models
# import uuid

# SCRAPPER_CHOICES = (
#     (0, "Individual"),
#     (1, "Employee"),
# )

# VEHICLE_TYPE_CHOICES = (
#     (0, "Car"),
#     (1, "SUV/Truck"),
#     (2, "Box Truck"),
# )

# class Scrapper(models.Model):
#   id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#   type = models.IntegerField(choices=SCRAPPER_CHOICES, null=True, blank=True)

#   def _str_(self):
#     return self.name_first + " " + self.name_last

# class Contact(models.Model):
#   scrapper = models.OneToOneField(
#     Scrapper,
#     on_delete=models.CASCADE,
#     primary_key=True
#   )
#   name_first = models.CharField(max_length=120, null=True, blank=True)
#   name_middle = models.CharField(max_length=120, null=True, blank=True)
#   name_last = models.CharField(max_length=120, null=True, blank=True)
#   phone = models.CharField(max_length=10, null=True, blank=True)
  
# class Vehicle(models.Model):
#   scrapper = models.OneToOneField(
#     Scrapper,
#     on_delete=models.CASCADE,
#     primary_key=True
#   )
#   type = models.IntegerField(choices=VEHICLE_TYPE_CHOICES, null=True, blank=True)
#   year = models.IntegerField(null=True, blank=True)
#   make = models.CharField(max_length=1024, null=True, blank=True)
#   model = models.CharField(max_length=1024, null=True, blank=True)
  
# class Address(models.Model):
#   scrapper = models.OneToOneField(
#     Scrapper,
#     on_delete=models.CASCADE,
#     primary_key=True
#   )
#   address = models.CharField(max_length=1024, null=True, blank=True)
#   city = models.CharField(max_length=1024, null=True, blank=True)
#   state = models.CharField(max_length=2, null=True, blank=True)
#   zipcode = models.CharField(max_length=6, null=True, blank=True)
#   latitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
#   longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)