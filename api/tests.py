from django.test import TestCase

# test xgboost_pricing.py module
from pricing_ml import price_model_xgb

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
