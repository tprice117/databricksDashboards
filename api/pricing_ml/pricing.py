import math
import pandas as pd
from api.models import DisposalLocation, DisposalLocationWasteType, Product, Seller, SellerLocation, SellerProduct, SellerProductSellerLocation
import googlemaps
import numpy as np
import json
import requests
import datetime  

class Price_Model:
    def __init__(self, request, model = None, enc = None):

        # Assign model and encoder
        self.model = model
        self.enc = enc

        # Product.
        self.product = Product.objects.get(id=request.data['product_id'])
        
        # always need customer lat and long
        self.customer_lat = float(request.data['customer_lat'])
        self.customer_long = float(request.data['customer_long'])

        # product characteristics required fields
        self.product_id = request.data['product_id']
        self.waste_type = request.data['waste_type']


        # Assign posted data to variables
        self.start_date = datetime.datetime.strptime(request.data['start_date'], '%Y-%m-%d') if 'start_date' in request.data else None
        self.end_date = datetime.datetime.strptime(request.data['end_date'], '%Y-%m-%d') if 'end_date' in request.data else None

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
        """Calc static junk price with distance from hauler to seller and diesel price."""
        try:
            # get diesel price from FRED
            fredid = 'GASDESW'
            latest_diesel = self.getdatafred(fredid, self.fred_api)
            diesel_price = latest_diesel.loc[:,'value'].iloc[-1]
        except:
            diesel_price = 5

        # Get SellerLocations that offer the product.
        seller_products = SellerProduct.objects.filter(product=self.product)
        seller_product_seller_locations = SellerProductSellerLocation.objects.filter(seller_product__in=seller_products)

        # Get prices for each SellerLocation. skip if distance is greater than 40 miles.
        seller_location_prices = []
        for seller_product_seller_location in seller_product_seller_locations:
            price_obj = self.get_price_for_seller_product_seller_location(seller_product_seller_location.id, diesel_price)
            if price_obj['total_distance'] <= 40:
                seller_location_prices.append(price_obj)
            else:
                print('Skipping seller_location: ', seller_product_seller_location.seller_location.id ,\
                       ' distance: ', price_obj['total_distance'])

        print(seller_location_prices)    

        return seller_location_prices
    
    def get_price_for_seller_product_seller_location(self, seller_product_seller_location_id, diesel_price):
        seller_product_seller_location = SellerProductSellerLocation.objects.get(id=seller_product_seller_location_id)

        # Get diesel_price if not provided.
        if diesel_price is None:
            try:
                fredid = 'GASDESW'
                latest_diesel = self.getdatafred(fredid, self.fred_api)
                diesel_price = latest_diesel.loc[:,'value'].iloc[-1]
            except:
                diesel_price = 5

        # static value now, change in future
        mpg = 6.5

        # Seller to Customer distance.
        lat1, lon1 = self.customer_lat, self.customer_long
        lat2, lon2 = seller_product_seller_location.seller_location.latitude, seller_product_seller_location.seller_location.longitude
        seller_customer_distance = self.get_driving_distance(lat1, lon1, lat2, lon2)

        # Find best disposal location.
        disposal_locations = DisposalLocation.objects.all()
        
        best_disposal_location = None
        best_total_distance = None
        for disposal_location in disposal_locations:
            customer_disposal_distance = self.get_euclidean_distance(self.customer_lat, self.customer_long, disposal_location.latitude, disposal_location.longitude)
            disposal_seller_distance = self.get_euclidean_distance(disposal_location.latitude, disposal_location.longitude, seller_product_seller_location.seller_location.latitude, seller_product_seller_location.seller_location.longitude)
            total_distance = seller_customer_distance + customer_disposal_distance #+ disposal_seller_distance

            if best_disposal_location is None or best_total_distance is None or total_distance < best_total_distance:
                best_disposal_location = disposal_location
                best_total_distance = total_distance
        
        # Calculate milage cost.
        milage_cost = (float(best_total_distance) / float(mpg)) * float(diesel_price)

        # Add tip fees for waste type multiplied by tons.
        disposal_location_waste_type = DisposalLocationWasteType.objects.get(disposal_location=best_disposal_location.id, waste_type=self.waste_type)
        included_tons = 4
        tip_fees = disposal_location_waste_type.price_per_ton * included_tons

        # Add daily rate.
        base_cost = None
        if self.product.main_product.main_product_category.main_product_category_code == "RO":
            base_cost =(self.end_date - self.start_date).days * 22 # assume $22 per day for roll off dumpsters
        elif self.product.main_product.main_product_category.main_product_category_code == "JR":
            # ascending order for junk removal, let's assume $100 for each CY, then discount for larger sizes
            # 1200 for median pricing for a XL junk removal from other sellers historically
            # XL = 16 CY, XXL = 20 CY
            if self.product.product_code == "JR3CY":
                base_cost = 113
            elif self.product.product_code == "JR4CY":
                base_cost = 249
            elif self.product.product_code == "JR5CY":
                base_cost = 349
            elif self.product.product_code == "JR8CY":
                base_cost = 379
            elif self.product.product_code == "JR10CY":
                base_cost = 479
            elif self.product.product_code == "JR12CY":
                base_cost = 509
            elif self.product.product_code == "JR16CY":
                base_cost = 639
            elif self.product.product_code == "JR20CY":
                base_cost = 699
            else:
                base_cost = 349 # assume $349 per CY for junk removal if no prod added

        return {
            'seller': seller_product_seller_location.seller_location.seller.id,
            'seller_location': seller_product_seller_location.seller_location.id,
            'seller_product_seller_location': seller_product_seller_location.id,
            'disposal_location': best_disposal_location.id,
            'milage_cost': milage_cost,
            'tip_fees': tip_fees,
            'rental_cost': base_cost,
            'total_distance' : total_distance,
            'price': float(milage_cost or 0.0) + float(tip_fees or 0.0) + float(base_cost or 0.0),
            'line_items': [
                {
                    'name': 'Milage Cost',
                    'price': milage_cost,
                },
                {
                    'name': 'Tip Fees',
                    'price': tip_fees,
                },
                {
                    'name': 'Base Cost',
                    'price': base_cost,
                },
            ]
        }