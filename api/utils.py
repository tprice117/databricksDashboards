import math
 

def get_distance(lat1, lon1, lat2, lon2):
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