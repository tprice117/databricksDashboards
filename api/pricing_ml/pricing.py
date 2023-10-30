import decimal
import math
import pandas as pd
import api.models
import googlemaps
import numpy as np
import json
import requests
import datetime  

class Price_Model:
    def __init__(self, data, model = None, enc = None):

        # Assign model and encoder
        self.model = model
        self.enc = enc

        # Seller Location (if passed).
        self.seller_location = api.models.SellerLocation.objects.get(id=data['seller_location']) if 'seller_location' in data and data['seller_location'] else None

        # Product.
        self.product = api.models.Product.objects.get(id=data['product'])

        # User Address.
        self.user_address = api.models.UserAddress.objects.get(id=data['user_address'])
        
        # Waste Type.
        self.waste_type = api.models.WasteType.objects.get(id=data['waste_type']) if 'waste_type' in data and data['waste_type'] else None

        self.google_maps_api = r'AIzaSyCKjnDJOCuoctPWiTQLdGMqR6MiXc_XKBE'
        self.fred_api = r'fa4d32f5c98c51ccb516742cf566950f'

    def get_driving_distance(self, lat1, lon1, lat2, lon2, unit='M'):
        """Use google maps api to calculate the driving distance between two points."""
        gmaps = googlemaps.Client(key=self.google_maps_api)
        try:
            distance = gmaps.distance_matrix((lat1, lon1), (lat2, lon2), mode='driving')['rows'][0]['elements'][0]['distance']['value']
            if unit == 'M':
                return distance * 0.000621371
            elif unit == 'K':
                return distance * 0.001
            else:
                return distance
        except:
            return np.nan
        
    def get_euclidean_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)
        """
        lat_a = math.radians(lat1)
        lat_b = math.radians(lat2)
        long_diff = math.radians(float(lon1) - float(lon2))
        distance = (math.sin(lat_a) * math.sin(lat_b) +
                    math.cos(lat_a) * math.cos(lat_b) * math.cos(long_diff))
        resToMile = math.degrees(math.acos(distance)) * 69.09
        return resToMile
        
    def getdatafred(self, fredid, apikey):
        """get data from FRED via API with item code, fredid, and apikey"""
        url = r'https://api.stlouisfed.org/fred/series/observations' + \
        '?series_id='  + fredid + \
        '&api_key=' + apikey + \
        '&file_type=json'
        x = requests.get(url)
        data = json.loads(x.text)
        df = pd.DataFrame(data['observations'])
        return df

    def preprocessing(self, input_data):
        # convert json to dataframe and encode categorical variables
        df = pd.DataFrame(input_data, index=[0]) 
        # collect these: Variable Costs: 'distance_miles', 'value' (diesel price), 'mpg' (static value)
        # Order charateristics (BASE): 'product_group', 'product_parent', 'waste_type','city_start', 'rental_type', 
        customer, hauler = df['customer_coordinates'], df['seller_coordinates']
        # variable costs (placeholder until we add apis or bucket accounts)
        try:
            # seller to buyer distance
            lat1, lon1 = customer
            lat2, lon2 = hauler
            distance_miles = self.get_driving_distance(lat1, lon1, lat2, lon2)
            # buyer to dump distance
            lat3, lon3 = 39.856575, -104.762587 # tower disposal site
            distance_miles += self.get_driving_distance(lat2, lon2, lat3, lon3)
        except:
            distance_miles = 35 # assume 35 miles if no address is given

        try:
            # get diesel price from FRED
            fredid = 'GASDESW'
            latest_diesel = self.getdatafred(fredid, self.fred_api)
            value = latest_diesel.loc[:,'value'].iloc[-1]
        except:
            value = 5 # assume $5/gallon if no diesel price is given
        
        # static value now, change in future
        mpg = 6.5

        catdat = df[['product_group', 'product_parent', 'waste_type', 'city_start', 'rental_type']]   
        
        # encode the base price characteristics and transform sparse matrix to dataframe
        encoded = self.enc.transform(catdat).toarray()
        # encode the base price characteristics and transform sparse matrix to dataframe
        cat_dat = pd.DataFrame(encoded, columns=self.enc.get_feature_names_out())

        # concat the base price characteristics with the variable costs
        df = pd.concat([pd.DataFrame({'distance_miles': distance_miles, 'value': value, 'mpg': mpg}, index=[0]),\
                        cat_dat], axis=1)
        
        return df
    
    def predict_price(self, input_data):
        try:
            # preprocess input data
            df = self.preprocessing(input_data)

            # make prediction
            prediction = self.model.predict(df)
            return float(prediction)
        
        except Exception as e:
            print(e)
            return {"status": "Error", "message": str(e)}
        
    def get_prices(self):
        # Get SellerLocations that offer the product.
        seller_products = api.models.SellerProduct.objects.filter(product=self.product)
        seller_product_seller_locations = api.models.SellerProductSellerLocation.objects.filter(seller_product__in=seller_products, active=True)
        

        if self.seller_location:
            # If SellerLocation is passed, only return price for that SellerLocation.
            seller_product_seller_location = seller_product_seller_locations.filter(seller_location=self.seller_location).first()
            return self.get_price_for_seller_product_seller_location(seller_product_seller_location)
        else:
            # Get prices for each SellerLocation. skip if distance is greater than 40 miles.
            seller_location_prices = []
            main_product_waste_types = api.models.MainProductWasteType.objects.filter(main_product=self.product.main_product)

            for seller_product_seller_location in seller_product_seller_locations:
                # Get distance between seller and customer.
                seller_customer_distance = self.get_driving_distance(
                    seller_product_seller_location.seller_location.latitude, 
                    seller_product_seller_location.seller_location.longitude,
                    self.user_address.latitude, 
                    self.user_address.longitude
                )

                # Get Material Waste Types for the SellerProductSellerLocation.
                if main_product_waste_types.count() > 0 and hasattr(seller_product_seller_location, 'material'):
                    material_waste_types = api.models.SellerProductSellerLocationMaterialWasteType.objects.filter(seller_product_seller_location_material=seller_product_seller_location.material)
                else:
                    material_waste_types = None

                # Only return Seller options within the service radius and that have the same waste type.
                customer_within_seller_service_radius = seller_customer_distance < (seller_product_seller_location.service_radius or 0)
                waste_type_match = main_product_waste_types.count() == 0 or (material_waste_types and material_waste_types.filter(main_product_waste_type__waste_type=self.waste_type).exists())
                if customer_within_seller_service_radius and waste_type_match:
                    price_obj = self.get_price_for_seller_product_seller_location(seller_product_seller_location)
                    seller_location_prices.append(price_obj)

            return seller_location_prices
    
    def get_price_for_seller_product_seller_location(self, seller_product_seller_location):
        main_product = seller_product_seller_location.seller_product.product.main_product

        # if main_product.has_service or main_product.has_material:
        #     disposal_location_waste_type = self.get_best_disposal_location(seller_product_seller_location)

        # Service price.
        service = self.get_service_price(seller_product_seller_location)

        # Rental
        rental = self.get_rental_price(seller_product_seller_location)

        # Material.
        material = self.get_material_price(seller_product_seller_location)

        return {
            'seller_product_seller_location': seller_product_seller_location.id,
            'service': service,
            'rental': rental,
            'material': material,
        }

    def get_service_price(self, seller_product_seller_location):
        if seller_product_seller_location.seller_product.product.main_product.has_service and hasattr(seller_product_seller_location, 'service'):
            service = seller_product_seller_location.service

            # Get pricing per mile.
            rate = None
            is_flat_rate = None
            if service.price_per_mile:
                rate = service.price_per_mile
                is_flat_rate = False
                
                # Seller to Customer distance.
                total_distance = self.get_driving_distance(
                    seller_product_seller_location.seller_location.latitude, 
                    seller_product_seller_location.seller_location.longitude,
                    self.user_address.latitude, 
                    self.user_address.longitude
                )

                # Cusotomer to Disposal Location distance.
                # disposal_location = DisposalLocation.objects.get(id=disposal_location_waste_type.id)
                # customer_disposal_location_distance = self.get_driving_distance(
                #     self.user_address.latitude, 
                #     self.user_address.longitude, 
                #     disposal_location.latitude, 
                #     disposal_location.longitude
                # )
            elif service.flat_rate_price:
                rate = service.flat_rate_price
                is_flat_rate = True
            
            return {
                "rate": rate,
                "is_flat_rate": is_flat_rate,
                "total_distance": total_distance if service.price_per_mile else None,
                # "customer_to_disposal_location_distance": customer_disposal_location_distance
            }
        else: 
            return None

    def get_rental_price(self, seller_product_seller_location):
        if seller_product_seller_location.seller_product.product.main_product.has_rental and hasattr(seller_product_seller_location, 'rental'):
            rental = seller_product_seller_location.rental
            
            return {
                "included_days": rental.included_days,
                "price_per_day_included": rental.price_per_day_included * decimal.Decimal(1.2) if rental.price_per_day_included else None,
                "price_per_day_additional": rental.price_per_day_additional * decimal.Decimal(1.2)  if rental.price_per_day_additional else None,
            }
        else:
            return None
    
    def get_material_price(self, seller_product_seller_location):
        if seller_product_seller_location.seller_product.product.main_product.has_material and hasattr(seller_product_seller_location, 'material'):
            material = seller_product_seller_location.material

            main_product_waste_type = api.models.MainProductWasteType.objects.get(
                main_product = seller_product_seller_location.seller_product.product.main_product,
                waste_type = self.waste_type
            )

            seller_product_seller_location_material_waste_type = api.models.SellerProductSellerLocationMaterialWasteType.objects.get(
                seller_product_seller_location_material = material,
                main_product_waste_type = main_product_waste_type
            ) if api.models.SellerProductSellerLocationMaterialWasteType.objects.filter(
                seller_product_seller_location_material = material,
                main_product_waste_type = main_product_waste_type
            ).exists() else None
            
            return {
                "tonnage_included": seller_product_seller_location_material_waste_type.tonnage_included if seller_product_seller_location_material_waste_type else None,
                "price_per_ton": seller_product_seller_location_material_waste_type.price_per_ton * decimal.Decimal(1.2)  if seller_product_seller_location_material_waste_type else None
            }
        else:
            return None

    def get_best_disposal_location(self, seller_product_seller_location):
        disposal_location_waste_types = api.models.DisposalLocationWasteType.objects.all(waste_type=self.waste_type)

        seller_customer_distance = self.get_driving_distance(
            seller_product_seller_location.seller_location.latitude, 
            seller_product_seller_location.seller_location.longitude,
            self.user_address.latitude, 
            self.user_address.longitude
        )
        
        disposal_location_waste_type = None
        best_total_distance = None
        for disposal_location_waste_type in disposal_location_waste_types:
            disposal_location = api.models.DisposalLocation.objects.get(id=disposal_location_waste_type.disposal_location)
            customer_disposal_distance = self.get_euclidean_distance(self.user_address.latitude, self.user_address.longitude, disposal_location.latitude, disposal_location.longitude)
            total_distance = seller_customer_distance + customer_disposal_distance

            if disposal_location_waste_type is None or best_total_distance is None or total_distance < best_total_distance:
                disposal_location_waste_type = disposal_location_waste_type
                best_total_distance = total_distance

        return disposal_location_waste_type