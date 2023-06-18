import googlemaps 
import numpy as np

google_maps_api = r'AIzaSyCKjnDJOCuoctPWiTQLdGMqR6MiXc_XKBE'

def get_driving_distance(lat1, lon1, lat2, lon2, unit='M'):
  """Use google maps api to calculate the driving distance between two points."""
  gmaps = googlemaps.Client(key=google_maps_api)
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
  
def geocode_address(address):
  """Use google maps api to geocode an address."""
  gmaps = googlemaps.Client(key=google_maps_api)
  try:
      print("Address: " + address)
      geocode_result = gmaps.geocode(address)
      print(geocode_result)
      lat = geocode_result[0]['geometry']['location']['lat']
      lng = geocode_result[0]['geometry']['location']['lng']
      return lat, lng
  except:
      return None, None