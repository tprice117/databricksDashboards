from django.test import TestCase, Client
# import json
# test xgboost_pricing.py module
# from pricing_ml import price_model_xgb
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import User
from django.contrib.admin.models import LogEntry, DELETION
from django.contrib.contenttypes.models import ContentType



# everything we need to test the api on the backend
# from .models import Seller, Product, Order, User
# from .serializers import SellerSerializer, ProductSerializer, OrderSerializer
from rest_framework import status
from rest_framework.test import APITestCase

### TEST PRICING MODULE ###
"""
class Pricetest(TestCase):
    def setUp(self):
        # test init function
        self.model = price_model_xgb
        self.input_data = {
        "customer_coordinates": [39.7392, -104.9903],
        "seller_coordinates": [39.7392, -104.9903],
        "product_group": "30 yard dumpster",
        "product_parent": "On-Demand",
        "waste_type": "Construction",
        "city_start": "Denver",
        "rental_type": "Long Term"
        }
    
    def predict(self):
        # test predict function
        test_pred = self.model.predict_price(self.input_data)
        self.assertIsInstance(test_pred, float) # just check that it's a float
"""

### TEST CRUD OPERATIONS ON ALL MODELS ###

class TestAddUser(TestCase):
    """ Test module for creating customers API """

    def setUp(self):
        self.client = Client()
        self.add_user_url = reverse('add_user')
        self.valid_data = {
            'first_name' : 'John', 
            'last_name':'Smith',
            'user_id' : 'johnsmith1',
            'phone' : '303-555-5555',
            'email' : 'johnsmith@test.com',
            'photo_url' : 'https://www.userimage.com/johnsmith1/home.jpg',
            # 'seller' : "",
            'stripe_customer_id' : '12345',
            'device_token' : '12345',
        }
        self.invalid_data = {
            'first_name' : 'John', 
            'last_name':'Smith',
            # 'user_id' : 'johnsmith1',
            'phone' : '303-555-5555',
            'email' : 'johnsmith@test.com',
            'photo_url' : 'https://www.userimage.com/johnsmith1/home.jpg',
            # 'seller' : None,
            # 'stripe_customer_id' : '12345',
            'device_token' : '12345',
        }

    def test_add_user_successfully(self):
        response = self.client.post(self.add_user_url, self.valid_data)
        self.assertEqual(response.status_code, 201)
        # Add additional assertions here

    def test_add_user_with_invalid_data(self):
        response = self.client.post(self.add_user_url, self.invalid_data)
        self.assertEqual(response.status_code, 400)
        # Add additional assertions here

from django.apps import apps
from django.test import TestCase, Client
from rest_framework import status
from rest_framework.test import APIClient

class CrudTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_all_models(self):
        # Get all models in the app
        models = [model for model in apps.get_models() if not model._meta.app_label.startswith('django')]

        # Get all models in the app excluding django_admin models
        models = [model for model in apps.get_models() if not model._meta.app_label.startswith('django_admin')]

        # Loop through all models
        for model in models:
            # Check if the model has any required fields
            required_fields = model._meta.fields
            required_fields = [field for field in required_fields if not field.blank and not field.null]

            if required_fields:
                # Skip testing this model if it has required fields
                continue

            # Create an instance of the model
            instance = model.objects.create()

            # Get the content type for the model
            content_type = ContentType.objects.get_for_model(model)

            # Get logs for the model
            logs = LogEntry.objects.filter(content_type=content_type)

            # Test GET all instances
            response = self.client.get(f'/{model._meta.verbose_name_plural}/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Test GET single instance
            response = self.client.get(f'/{model._meta.verbose_name_plural}/{instance.id}/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Test POST
            data = {'name': 'New instance'}
            response = self.client.post(f'/{model._meta.verbose_name_plural}/', data=data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            # Test PUT
            data = {'name': 'Updated instance'}
            response = self.client.put(f'/{model._meta.verbose_name_plural}/{instance.id}/', data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Test that no logs were created for django_admin actions
            for log in logs:
                if log.action_flag == DELETION and log.object_id == str(instance.id):
                    # Handle the case where a record was deleted
                    self.fail(f'Deleted {model._meta.verbose_name} was logged in django_admin')
                elif log.action_flag != DELETION and log.object_id == str(instance.id):
                    # Handle the case where a record was added or changed
                    pass
