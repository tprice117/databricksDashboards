from uuid import uuid4
from django.conf import settings
import requests
import api.models
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

def get_price_for_seller(seller_product_seller_location, customer_lat, customer_long, waste_type, start_date, end_date, disposal_locations):
  # Find closest DisposalLocation between customer and business.
  best_disposal_location = None
  best_total_distance = None
  for disposal_location in disposal_locations:
    seller_customer_distance = get_distance(seller_product_seller_location.seller_location.latitude, seller_product_seller_location.seller_location.longitude, customer_lat, customer_long)
    customer_disposal_distance = get_distance(customer_lat, customer_long, disposal_location.latitude, disposal_location.longitude)
    disposal_seller_distance = get_distance(disposal_location.latitude, disposal_location.longitude, seller_product_seller_location.seller_location.latitude, seller_product_seller_location.seller_location.longitude)
    total_distance = seller_customer_distance + customer_disposal_distance #+ disposal_seller_distance

    if best_disposal_location is None or best_total_distance is None or total_distance < best_total_distance:
      best_disposal_location = disposal_location
      best_total_distance = total_distance

  # Calculate milage cost.
  milage_cost = best_total_distance * 5

  # Add tip fees for waste type multiplied by tons.
  disposal_location_waste_type = api.models.DisposalLocationWasteType.objects.get(disposal_location=best_disposal_location.id, waste_type=waste_type)
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
        'name': 'Rental Cost',
        'price': rental_cost,
      },
    ]
  }

# Helper methods.
def get_auth0_access_token():
    # Get access_token.
    payload = {
        "client_id": settings.AUTH0_CLIENT_ID,
        "client_secret": settings.AUTH0_CLIENT_SECRET,
        "audience":"https://" + settings.AUTH0_DOMAIN + "/api/v2/",
        "grant_type":"client_credentials"
    }
    headers = { 'content-type': "application/json" }
    response = requests.post(
        'https://' + settings.AUTH0_DOMAIN + '/oauth/token',
        json=payload,
        headers=headers,
        timeout=5,
    )
    return response.json()["access_token"]

def create_user(email):
    headers = { 'authorization': "Bearer " +  get_auth0_access_token() }
    response = requests.post(
        'https://' + settings.AUTH0_DOMAIN + '/api/v2/users',
        json={
          "email": email,
          "connection": "Username-Password-Authentication",
          "password": str(uuid4())[:12],
        },
        headers=headers,
        timeout=30,
    )
    return response.json()['user_id'] if 'user_id' in response.json() else None

def get_user_data(user_id):
    headers = { 'authorization': "Bearer " +  get_auth0_access_token() }
    response = requests.get(
        'https://' + settings.AUTH0_DOMAIN + '/api/v2/users/' + user_id,
        headers=headers,
        timeout=30,
    )
    return response.json()

def get_user_from_email(email):
    headers = { 'authorization': "Bearer " +  get_auth0_access_token() }
    response = requests.get(
        'https://' + settings.AUTH0_DOMAIN + '/api/v2/users-by-email?email=' + email,
        headers=headers,
        timeout=30,
    )
    json = response.json()
    return json[0]['user_id'] if len(json) > 0 and 'user_id' in json[0] else None

def delete_user(user_id):
    if user_id is not None:
        headers = { 'authorization': "Bearer " +  get_auth0_access_token() }
        response = requests.delete(
            'https://' + settings.AUTH0_DOMAIN + '/api/v2/users/' + user_id,
            headers=headers,
            timeout=30,
        )
        return response.json()
    

#### DENVER COMP REPORT ####
import datetime
# from api.models import Order, OrderDisposalTicket, UserAddress
import mailchimp_transactional as MailchimpTransactional
from mailchimp_transactional.api_client import ApiClientError
from django.template.loader import render_to_string

def send_denver_compliance_report(user_address_id, user_email):
    user_address = api.models.UserAddress.objects.get(pk=user_address_id)
    orders = api.models.Order.objects.filter(user_address=user_address)
    order_disposal_tickets = api.models.OrderDisposalTicket.objects.filter(order__in=orders)
    print(order_disposal_tickets)

    # Create header object.
    header_objects = {
        "applicant_name": user_address.user_group.name if user_address.user_group else "",
        "project_address": user_address.street,
        "permit_number": "N/A",
        "phone": "000-000-0000",
        "date_completed": datetime.datetime.now().strftime("%m/%d/%Y"),
    }

    # Create array for disposal tickets.
    order_disposal_tickets_inputs = []
    for ticket in order_disposal_tickets:
        order_disposal_tickets_inputs.append({
            "date": ticket.created_on.strftime("%m/%d/%Y"),
            "weight_ticket_id": ticket.ticket_id,
            "landfill": str(ticket.weight) if ticket.waste_type.name == "Trash (Household Goods)" else "",
            "wood": str(ticket.weight) if ticket.waste_type.name == "Wood" else "",
            "concrete_brick_block": str(ticket.weight) if ticket.waste_type.name == "Concrete (No metal)" else "",
            "asphalt": str(ticket.weight) if ticket.waste_type.name == "Asphalt" else "",
            "metal": str(ticket.weight) if ticket.waste_type.name == "Mixed Metal" else "",
            "cardboard": str(ticket.weight) if ticket.waste_type.name == "Cardboard" else "",
            "donation_reuse": str(ticket.weight) if ticket.waste_type.name == "Salvage for Donation/Reuse" else "",
            "other": "",
            "total_diversion": str(ticket.weight) if ticket.waste_type.name != "Trash (Household Goods)"  else "0",
            "total_cd_debris": str(ticket.weight),
            "hauler": ticket.order.seller_product_seller_location.seller_location.seller.name,
            "destination": ticket.disposal_location.name,
        })

    # Create object for totals.
    total_diversion = order_disposal_tickets.exclude(waste_type__name="Trash (Household Goods)").aggregate(Sum('weight'))['weight__sum']
    total_cd_debris = order_disposal_tickets.aggregate(Sum('weight'))['weight__sum']
    totals = {
        "landfill": order_disposal_tickets.filter(waste_type__name="Trash (Household Goods)").aggregate(Sum('weight'))['weight__sum'] or "0",
        "wood": order_disposal_tickets.filter(waste_type__name="Wood").aggregate(Sum('weight'))['weight__sum'] or "0",
        "concrete_brick_block": order_disposal_tickets.filter(waste_type__name="Concrete (No metal)").aggregate(Sum('weight'))['weight__sum'] or "0",
        "asphalt": order_disposal_tickets.filter(waste_type__name="Asphalt").aggregate(Sum('weight'))['weight__sum'] or "0",
        "metal": order_disposal_tickets.filter(waste_type__name="Mixed Metal").aggregate(Sum('weight'))['weight__sum'] or "0",
        "cardboard": order_disposal_tickets.filter(waste_type__name="Cardboard").aggregate(Sum('weight'))['weight__sum'] or "0",
        "donation_reuse": order_disposal_tickets.filter(waste_type__name="Salvage for Donation/Reuse").aggregate(Sum('weight'))['weight__sum'] or "0",
        "other": "0",
        "total_diversion": total_diversion,
        "total_cd_debris": total_cd_debris,
        "project_diversion_rate": round(100 * float(total_diversion) / float(total_cd_debris), 2) if total_cd_debris else 0,
    }

    mailchimp = MailchimpTransactional.Client("md-U2XLzaCVVE24xw3tMYOw9w")
    response = mailchimp.messages.send({"message": {
        "from_name": "Downstream",
        "from_email": "hello@trydownstream.io",
        "to": [
            {
                "email": user_email,
            },
            {
                "email": "thayes@trydownstream.io"
            }
        ],
        "subject": "Waste Compliance Report Export",
        "track_opens": True,
        "track_clicks": True,
        "html": render_to_string(
            'denver-compliance-form.html',
            {
                "order_disposal_tickets_inputs": order_disposal_tickets_inputs,
                "header_objects": header_objects,
                "totals": totals,
            }
        ),
        # "attachments": [
        #    {
        #         "type": "text/csv",
        #         "name": "waste_compliance_report.csv",
        #         "content": base64.b64encode(csv).decode("utf-8"),
        #    }
        # ]
    }})
    print(response)