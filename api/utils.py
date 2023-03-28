import math

from api.models import DisposalLocationWasteType
 

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

def get_price_for_seller(seller_product_seller_location, customer_lat, customer_long, waste_type, start_date, end_date, disposal_locations):
  # Find closest DisposalLocation between customer and business.
  best_disposal_location = None
  best_total_distance = None
  for disposal_location in disposal_locations:
    seller_customer_distance = get_distance(seller_product_seller_location.seller_location.latitude, seller_product_seller_location.seller_location.longitude, customer_lat, customer_long)
    customer_disposal_distance = get_distance(customer_lat, customer_long, disposal_location.latitude, disposal_location.longitude)
    disposal_seller_distance = get_distance(disposal_location.latitude, disposal_location.longitude, seller_product_seller_location.seller_location.latitude, seller_product_seller_location.seller_location.longitude)
    total_distance = (3 * seller_customer_distance) + customer_disposal_distance + disposal_seller_distance

    if best_disposal_location is None or best_total_distance is None or total_distance < best_total_distance:
      best_disposal_location = disposal_location
      best_total_distance = total_distance

  # Calculate milage cost.
  milage_cost = best_total_distance * 5

  # Add tip fees for waste type multiplied by tons.
  disposal_location_waste_type = DisposalLocationWasteType.objects.get(disposal_location=best_disposal_location.id, waste_type=waste_type)
  included_tons = 4
  tip_fees = disposal_location_waste_type.price_per_ton * included_tons

  # Add daily rate.
  rental_cost = (end_date - start_date).days * 22

  return {
    'seller': seller_product_seller_location.seller_location.seller.id,
    'seller_location': seller_product_seller_location.seller_location.id,
    'seller_product_seller_location': seller_product_seller_location.id,
    'disposal_location': best_disposal_location.id,
    'milage_cost': milage_cost,
    'tip_fees': tip_fees,
    'rental_cost': rental_cost,
    'price': float(milage_cost) + float(tip_fees) + float(rental_cost),
  }