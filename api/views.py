from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from rest_framework import viewsets
from .serializers import *
from .models import *
from django.conf import settings
import stripe
import requests
import json
from datetime import datetime
from django.utils.dateparse import parse_datetime
from random import randint

# To DO: Create GET, POST, PUT general methods.
stripe.api_key = settings.STRIPE_SECRET_KEY

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    filterset_fields = ["id", "user_id"]

class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.filter(type__in=["Customer", "Partner"])
    serializer_class = AccountSerializer
    filterset_fields = ["id", "parent"]

class AccountContactViewSet(viewsets.ModelViewSet):
    # queryset = AccountContactRelation.objects.filter(contact__is_user=True)
    queryset = AccountContactRelation.objects.all()
    serializer_class = AccountContactSerializer
    filterset_fields = ["id", "account", "contact"]

class OpportunityViewSet(viewsets.ModelViewSet):
    queryset = Opportunity.objects.all()
    serializer_class = OpportunitySerializer
    filterset_fields = ["id", "account", "is_closed"]

class MainProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = MainProductCategory.objects.all()
    serializer_class = MainProductCategorySerializer

class ProductCategoryInfoViewSet(viewsets.ModelViewSet):
    queryset = ProductCategoryInfo.objects.all()
    serializer_class = ProductCategoryInfoSerializer
    filterset_fields = ["product_category"]

class MainProductViewSet(viewsets.ModelViewSet):
    queryset = MainProduct.objects.all()
    serializer_class = MainProductSerializer
    filterset_fields = ["id", "product_category"]

class MainProductInfoViewSet(viewsets.ModelViewSet):
    queryset = MainProductInfo.objects.all()
    serializer_class = MainProductInfoSerializer
    filterset_fields = ["main_product"]    

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product2.objects.all()
    serializer_class = ProductSerializer
    filterset_fields = ["service_provider", "main_product"]   

# class MainProductFrequencyViewSet(viewsets.ModelViewSet):
#     queryset = MainProductFrequency.objects.all()
#     serializer_class = MainProductFrequencySerializer
#     filterset_fields = ["main_product"]  

class PriceBookViewSet(viewsets.ModelViewSet):
    queryset = Pricebook2.objects.all()
    serializer_class = PriceBookSerializer
    filterset_fields = ["is_standard"]  

class PriceBookEntryViewSet(viewsets.ModelViewSet):
    queryset = PricebookEntry.objects.all()
    serializer_class = PriceBookEntrySerializer
    filterset_fields = ["pricebook2", "product2"]  

class MainProductAddOnViewSet(viewsets.ModelViewSet):
    queryset = MainProductAddOn.objects.all()
    serializer_class = MainProductAddOnSerializer
    filterset_fields = ["main_product", "add_on"] 
  
class ProductAddOnChoiceViewSet(viewsets.ModelViewSet):
    queryset = ProductAddOnChoice.objects.all()
    serializer_class = ProductAddOnChoiceSerializer
    filterset_fields = ["product", "add_on_choice"] 

class AddOnViewSet(viewsets.ModelViewSet):
    queryset = AddOn.objects.all()
    serializer_class = AddOnSerializer

class AddOnChoiceViewSet(viewsets.ModelViewSet):
    queryset = AddOnChoice.objects.all()
    serializer_class = AddOnChoiceSerializer
    filterset_fields = ["add_on"] 

class LocationZoneViewSet(viewsets.ModelViewSet):
    queryset = LocationZone.objects.all()
    serializer_class = LocationZoneSerializer
    # filterset_fields = [""] 

class PostalCodeViewSet(viewsets.ModelViewSet):
    queryset = PostalCode.objects.all()
    serializer_class = PostalCodeSerializer
    filterset_fields = ["name"] 
    
class PriceBookViewSet(viewsets.ModelViewSet):
    queryset = Pricebook2.objects.all()
    serializer_class = PriceBookSerializer

class PriceBookEntryViewSet(viewsets.ModelViewSet):
    queryset = PricebookEntry.objects.all()
    serializer_class = PriceBookEntrySerializer
    filterset_fields = ["product2", "pricebook2"] 

baseUrl = "https://api.thetrashgurus.com/v2/"
MAX_RETRIES = 5
API_KEY = '556b608df74309034553676f5d4425401ae6c2fc29db793a5b1501'

def call_TG_API(url, payload):
  attempt_num = 0  # keep track of how many times we've retried
  while attempt_num < MAX_RETRIES:
      response = requests.post(url, json=payload)
      if response.status_code == 200:
          data = response.json()
          return Response(data, status=status.HTTP_200_OK)
      else:
          attempt_num += 1
          # You can probably use a logger to log the error here
          time.sleep(5)  # Wait for 5 seconds before re-trying
  return Response({"error": "Request failed"}, status=r.status_code)

def get(endpoint, body):
  url =  baseUrl + endpoint
  # payload = {"api_key": API_KEY} | body
  payload = dict({"api_key": API_KEY}.items() | body.items())
  return call_TG_API(url, payload)

def post(endpoint, body):
  url =  baseUrl + endpoint
  payload = {**{"api_key": API_KEY}, **body}
  print(payload)
  return call_TG_API(url, payload)

def put(endpoint, body):
  url =  baseUrl + endpoint
  payload = dict({"api_key": API_KEY}.items() | body.items())
  return call_TG_API(url, payload)

def delete(endpoint, body):
  url =  baseUrl + endpoint
  payload = dict({"api_key": API_KEY}.items() | body.items())
  return call_TG_API(url, payload)


class TaskView(APIView):
    def get(self, request, pk=None, *args, **kwargs):  
      if pk or request.query_params.get('job_id'):
        ids = []
        ids.append(int(pk or request.query_params.get('job_id')))
        return post("get_job_details", {
          "job_ids": ids,
          "include_task_history": 0
        })
      if request.query_params.get('customer_id'):
        return post("get_all_tasks", {"job_type": 3, "customer_id": int(request.query_params.get('customer_id'))})
      else:
        response = post("get_all_tasks", {"job_type": 3, "is_pagination": 0})
        new_list = []
        for data in response.data["data"]:
          new_list.append({**data, **{"time_start": 0, "time_end": 0}})
        response.data["data"] = new_list
        return response

    def post(self, request, *args, **kwargs):
      # account = Account.objects.get(id=request.data["customer_comment"])
      # job_delivery_datetime = parse_datetime(request.data["job_delivery_datetime"])
      # job_pickup_datetime = parse_datetime(request.data["job_pickup_datetime"])
      new_data = {
          **request.data, 
          # **{
          #   "customer_username": account.name,
          #   "customer_phone": account.phone or "1234567890",
          #   "customer_address": account.shipping_street + ", " + account.shipping_city + ", " + account.shipping_state,
          #   "latitude": str(account.shipping_latitude),
          #   "longitude": str(account.shipping_longitude),
          #   # "job_pickup_datetime": job_pickup_datetime.strftime("%Y-%m-%d") + " " + str(request.data["time_start"]).zfill(2) + ":00:00",
          #   # "job_delivery_datetime": job_delivery_datetime.strftime("%Y-%m-%d") + " " + str(request.data["time_end"]).zfill(2) + ":00:00",
          #    "job_pickup_datetime": job_pickup_datetime.strftime("%Y-%m-%d") + " " + str(request.data["time_start"]).zfill(2) + ":00:00",
          #   "job_delivery_datetime": job_delivery_datetime.strftime("%Y-%m-%d") + " " + str(request.data["time_end"]).zfill(2) + ":00:00",
          #   "has_pickup": "0",
          #   "has_delivery": "0",
          #   "layout_type": "1",
          #   "tracking_link": 1,
          #   "auto_assignment": "0",
          #   "notify": 1,
          #   "tags":"",
          #   "geofence":0,
          # } 
        }
      return post("create_task", new_data)

    def put(self, request, pk=None, *args, **kwargs):
      player_object = self.get_object(pk or request.query_params.get('id'))
      return put("edit_task", request.data)
    
    def delete(self, request, pk=None, *args, **kwargs):
      return delete("delete_task", {"job_id": pk or request.query_params.get('id')})

class AgentView(APIView):
    def get(self, request, pk=None, *args, **kwargs):   
      if pk or request.query_params.get('id'):   
        return post("view_fleet_profile", {"fleet_id": pk or request.query_params.get('id')})
      else:  
        response = get("get_all_fleets", {})
        new_list = []
        for data in response.data["data"]:
          new_list.append({**data, **{"team_id": 0, "first_name": ""}})
        response.data["data"] = new_list
        return response

    def post(self, request, *args, **kwargs):
      return post("add_agent", request.data)

    def put(self, request, pk=None, *args, **kwargs):
      player_object = self.get_object(pk or request.query_params.get('id'))
      return put("edit_agent", request.data)
    
    def delete(self, request, pk=None, *args, **kwargs):
      return delete("delete_fleet_account", {"team_id": pk or request.query_params.get('id')})

class TeamView(APIView):
    def get(self, request, pk=None, *args, **kwargs):     
      if pk or request.query_params.get('id'):   
        return post("view_teams", {"team_id": pk or request.query_params.get('id')})
      else:  
        return get("view_all_team_only", {})

    def post(self, request, *args, **kwargs):
      return post("create_team", request.data)

    def put(self, request, pk=None, *args, **kwargs):
        player_object = self.get_object(pk or request.query_params.get('id'))
        return put("update_team", request.data)
    
    def delete(self, request, pk=None, *args, **kwargs):
      return delete("delete_team", {"team_id": pk or request.query_params.get('id')})

class ManagerView(APIView):
    def get(self, request, pk=None, *args, **kwargs):     
      return get("view_all_manager")

    def post(self, request, *args, **kwargs):
      return post("add_manager", request.data)
    
    def delete(self, request, pk=None, *args, **kwargs):
      return delete("delete_manager", {"dispatcher_id": pk or request.query_params.get('id')})

class CustomerView(APIView):
    def get(self, request, pk=None, *args, **kwargs):     
      if pk or request.query_params.get('id'):   
        return post("view_customer_profile", {"customer_id": pk or request.query_params.get('id')})
      else:       
        return get("get_all_customers", {})

    def post(self, request, *args, **kwargs):
      return post("customer/add",
        {
          "user_type": 0, 
          "name": request.data["customer_email"], 
          "email": request.data["customer_email"], 
          "phone": randint(1000000000, 9999999999),
        }
    )

    def put(self, request, pk=None, *args, **kwargs):
        player_object = self.get_object(pk or request.query_params.get('id'))
        return put("customer/edit", request.data)
    
    def delete(self, request, pk=None, *args, **kwargs):
      return delete("delete_customer", {"customer_id": pk or request.query_params.get('id')})

class MerchantView(APIView):
    def post(self, request, *args, **kwargs):
      return post("merchant/sign_up", request.data)

    def put(self, request, pk=None, *args, **kwargs):
        player_object = self.get_object(pk or request.query_params.get('id'))
        return put("merchant/edit_merchant", request.data)
    
    def delete(self, request, pk=None, *args, **kwargs):
      return delete("merchant/delete", {"merchant_id": pk or request.query_params.get('id')})

class MissionView(APIView):
    def get(self, request, pk=None, *args, **kwargs):     
      return get("get_mission_list")

    def post(self, request, *args, **kwargs):
      return post("create_mission_task", request.data)
    
    def delete(self, request, pk=None, *args, **kwargs):
      return delete("delete_mission", {"mission_id": pk or request.query_params.get('id')})

class ConvertSFOrderToScrapTask(APIView):
    def get(self, request, pk=None, *args, **kwargs):
        order = Order.objects.get(order_number=pk)
        account = Account.objects.get(id=order.account_id)
        service_provider = Order.objects.get(id=order.service_provider)
        return post("create_task", {
              "order_id": order.order_number,
              "customer_username": account.name,
              "customer_phone": account.phone or "1234567890",
              "customer_address": account.shipping_street + ", " + account.shipping_city + ", " + account.shipping_state,
              "latitude": str(account.shipping_latitude),
              "longitude": str(account.shipping_longitude),
              "job_pickup_datetime": order.start_date_time.strftime("%Y-%m-%d %H:%m:%s"), #add field to salesforce object
              "job_delivery_datetime": order.start_date_time.strftime("%Y-%m-%d %H:%m:%s"), # add field to salesforce object
              "has_pickup": "0",
              "has_delivery": "0",
              "layout_type": "1",
              "tracking_link": 1,
              "auto_assignment": "0",
              "timezone": "-420",
              "notify": 1,
              "tags":"",
              "geofence":0,
              "team_id": service_provider.scrap_team_id,
              "fleet_id": service_provider.scrap_fleet_id,
            }
        )



### Stripe Views

class StripePaymentMethods(APIView):
    def get(self, request, format=None):
        stripe_customer_id = self.request.query_params.get('id')
        print(stripe_customer_id)
        payment_methods = stripe.Customer.list_payment_methods(
            stripe_customer_id,
            type="card",
        )
        return Response(payment_methods)

class StripeSetupIntents(APIView):
    def get(self, request, format=None):
        stripe_customer_id = self.request.query_params.get('id')
  
        # Create Setup Intent.
        setup_intent = stripe.SetupIntent.create(
            customer=stripe_customer_id,
            payment_method_types=["card"],
            usage="off_session",
        )

        # Create ephemeral key and add to reponse.
        ephemeralKey = stripe.EphemeralKey.create(
            customer=stripe_customer_id,
            stripe_version='2020-08-27',
        )
        setup_intent["ephemeral_key"] = ephemeralKey.secret
        return Response(setup_intent)

class StripePaymentIntents(APIView):
    def get(self, request, format=None):
        stripe_customer_id = self.request.query_params.get('customer_id')
        amount = self.request.query_params.get('amount')
  
        # Create Setup Intent.
        payment_intent = stripe.PaymentIntent.create(
            customer=stripe_customer_id,
            payment_method_types=["card"],
            amount=amount,
            currency='usd',
        )

        # Create ephemeral key and add to reponse.
        ephemeralKey = stripe.EphemeralKey.create(
            customer=stripe_customer_id,
            stripe_version='2020-08-27',
        )
        payment_intent["ephemeral_key"] = ephemeralKey.secret
        return Response(payment_intent)

class StripeCreateCheckoutSession(APIView):
    def get(self, request, format=None):
        customer_id = self.request.query_params.get('customer_id')
        price_id = self.request.query_params.get('price_id')
        mode = self.request.query_params.get('mode')

        session = stripe.checkout.Session.create(
            customer=customer_id,
            success_url="https://success.com",
            cancel_url="https://cancel.com",
            line_items=[
                {
                "price": price_id,
                "quantity": 1,
                },
            ],
            mode=mode,
        )
        return Response(session)

class StripeConnectPayoutForService(APIView):
    # Payout Accepted Vendor for Service Request.
    def get(self, request, pk, format=None):
        service_request = ServiceRequest.objects.get(pk=pk)

        # Get accpeted quote (will error if more than 1 accepted).
        accepted_quote = service_request.quotes.get(accepted=True)

        # Calculate the total amount_received for this service request.
        payment_intents = stripe.PaymentIntent.search(
            query='metadata["service_request_id"]:"' + str(service_request.id) + '"'
        )
        total_received = sum(payment_intent.amount_received for payment_intent in payment_intents)
       
        # Calculate the total amount payed out to the vendor.
        transfers = stripe.Transfer.list(transfer_group=str(service_request.id))
        total_transferred = sum(transfer.amount for transfer in transfers)

        # Calculate Hohm fee.
        customer_fee_ratio = service_request.platform_fee / 100
        vendor_fee_ratio = accepted_quote.platform_fee / 100

        customer_fee_dollar = total_received * customer_fee_ratio
        vendor_fee_dollar = (total_received - customer_fee_dollar) * vendor_fee_ratio
        total_platform_fee_dollar = customer_fee_dollar + vendor_fee_dollar

        # Transfer remaining vendor-payout (considering what has already been transffered).
        total_payout = total_received - total_platform_fee_dollar
        remaining_transfer_amount = total_payout - total_transferred
        if round(remaining_transfer_amount) > 1:
            transfer = stripe.Transfer.create(
                amount=round(remaining_transfer_amount),
                currency="usd",
                destination=accepted_quote.vendor.connect_express_account_id,
                transfer_group=service_request.id,
            )
            return Response(transfer)
        else:
            return Response()
        
## Stripe Dashboarding (GET only endpoints)

class StripeConnectAccount(APIView):
    def get(self, request, format=None):
        has_more = True
        starting_after = None
        data = []
        while has_more:
            accounts = stripe.Account.list(limit=100, starting_after=starting_after)
            data = data + accounts["data"]
            has_more = accounts["has_more"]
            starting_after = data[-1]["id"]
        return Response(data)

class StripeConnectTransfer(APIView):
    def get(self, request, format=None):
        has_more = True
        starting_after = None
        data = []
        while has_more:
            transfers = stripe.Transfer.list(limit=100, starting_after=starting_after)
            data = data + transfers["data"]
            has_more = transfers["has_more"]
            starting_after = data[-1]["id"]
        return Response(data)

class StripeBillingInvoice(APIView):
    def get(self, request, format=None):
        has_more = True
        starting_after = None
        data = []
        while has_more:
            invoices = stripe.Invoice.list(limit=100, starting_after=starting_after)
            data = data + invoices["data"]
            has_more = invoices["has_more"]
            starting_after = data[-1]["id"]
        return Response(data)

class StripeBillingSubscription(APIView):
    def get(self, request, format=None):
        has_more = True
        starting_after = None
        data = []
        while has_more:
            subscriptions = stripe.Subscription.list(limit=100, starting_after=starting_after)
            data = data + subscriptions["data"]
            has_more = subscriptions["has_more"]
            starting_after = data[-1]["id"]
        return Response(data)

class StripeCorePaymentIntents(APIView):
    def get(self, request, format=None):
        has_more = True
        starting_after = None
        data = []
        while has_more:
            payment_intents = stripe.PaymentIntent.list(limit=100, starting_after=starting_after)
            data = data + payment_intents["data"]
            has_more = payment_intents["has_more"]
            starting_after = data[-1]["id"]
        return Response(data)

