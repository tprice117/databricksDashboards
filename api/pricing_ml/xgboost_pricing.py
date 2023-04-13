import pandas as pd
import googlemaps
import numpy as np
import json
import requests

class price_model:
    def __init__(self, model = None, enc = None):
        self.model = model
        self.enc = enc
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
        
    def junk_price(self, input_data):
        