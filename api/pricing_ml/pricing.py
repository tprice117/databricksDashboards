import pandas as pd
import googlemaps
import numpy as np
import json
import requests
import datetime  

class Price_Model:
    def __init__(self, request, hauler_loc, model = None, enc = None):

        # Assign model and encoder
        self.model = model
        self.enc = enc

        # always need customer lat and long
        self.customer_lat = request.data['customer_lat'].astype(float)
        self.customer_long = request.data['customer_long'].astype(float)

        # always need business lat and long or one seller to process pricing request
        self.business_lat = hauler_loc.seller_location.latitude # process this request in views
        self.business_long = hauler_loc.seller_location.longitude # process this request in views

        # product characteristics required fields
        self.product_id = request.data['product_id']
        self.waste_type = request.data['waste_type']


        # assign logic for junk pricing; don't need dates for pricing junk
        if self.waste_type == 'Junk':
            self.start_date = None
            self.end_date = None
        else:
            # Assign posted data to variables
            self.start_date = datetime.datetime.strptime(request.data['start_date'], '%Y-%m-%d')
            self.end_date = datetime.datetime.strptime(request.data['end_date'], '%Y-%m-%d')


        self.google_maps_api = r'AIzaSyCKjnDJOCuoctPWiTQLdGMqR6MiXc_XKBE'
        self.fred_api = r'fa4d32f5c98c51ccb516742cf566950f'

    def distance(self, lat1, lon1, lat2, lon2):
        """Use google maps api to calculate the driving distance between two points."""
        gmaps = googlemaps.Client(key=self.google_maps_api)
        try:
            return gmaps.distance_matrix((lat1, lon1), (lat2, lon2), mode='driving')['rows'][0]['elements'][0]['distance']['value']
        except:
            return np.nan
        
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
            distance_miles = self.distance(lat1, lon1, lat2, lon2)
            # buyer to dump distance
            lat3, lon3 = 39.856575, -104.762587 # tower disposal site
            distance_miles += self.distance(lat2, lon2, lat3, lon3)
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
        
    def junk_price(self):
        """Calc static junk price with distance from hauler to seller and diesel price."""
        try:
            # get diesel price from FRED
            fredid = 'GASDESW'
            latest_diesel = self.getdatafred(fredid, self.fred_api)
            value = latest_diesel.loc[:,'value'].iloc[-1]
        except:
            value = 5

        # static value now, change in future
        mpg = 6.5

        # seller to buyer distance
        lat1, lon1 = self.customer_lat, self.customer_long
        lat2, lon2 = self.business_lat, self.business_long
        distance_miles = self.distance(lat1, lon1, lat2, lon2)

        # set junk base price
        if self.product == 'Junk - Extra Large':
            base_price = 1200
        elif self.product == 'Junk - Large':
            base_price = 1000
        elif self.product == 'Junk - Medium':
            base_price = 800
        elif self.product == 'Junk - Small':
            base_price = 600
        else:
            base_price = 500

        # calculate price components
        self.base_price = base_price
        self.variable_cost = (distance_miles / mpg) * value

        return self.base_price + self.variable_cost