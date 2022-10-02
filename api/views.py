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

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.filter(type__in=["Customer", "Partner"])
    serializer_class = AccountSerializer
    filterset_fields = ["id", "parent"]

class OpportunityViewSet(viewsets.ModelViewSet):
    queryset = Opportunity.objects.all()
    serializer_class = OpportunitySerializer

class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer

class ProductCategoryInfoViewSet(viewsets.ModelViewSet):
    queryset = ProductCategoryInfo.objects.all()
    serializer_class = ProductCategoryInfoSerializer
    filterset_fields = ["product_category"]

class MainProductViewSet(viewsets.ModelViewSet):
    queryset = MainProduct.objects.all()
    serializer_class = MainProductSerializer
    filterset_fields = ["product_category"]

class MainProductInfoViewSet(viewsets.ModelViewSet):
    queryset = MainProductInfo.objects.all()
    serializer_class = MainProductInfoSerializer
    filterset_fields = ["main_product"]    

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product2.objects.all()
    serializer_class = ProductSerializer
    filterset_fields = ["service_provider", "parent_product"]   

class MainProductFrequencyViewSet(viewsets.ModelViewSet):
    queryset = MainProductFrequency.objects.all()
    serializer_class = MainProductFrequencySerializer
    filterset_fields = ["main_product"]  

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
    filterset_fields = ["main_product_frequency"] 

class MainProductAddOnChoiceViewSet(viewsets.ModelViewSet):
    queryset = MainProductAddOnChoice.objects.all()
    serializer_class = MainProductAddOnChoiceSerializer
    

baseUrl = "https://api.thetrashgurus.com/v2/"
MAX_RETRIES = 5
API_KEY = '556b608df74309034553676f5d4425401ae6c2fc29db793a5b1501'

def call_TG_API(url, payload):
  attempt_num = 0  # keep track of how many times we've retried
  while attempt_num < MAX_RETRIES:
      response = requests.post(url, data = payload)
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
      if pk or request.query_params.get('id'):   
        return post("get_job_details_by_order_id", {"order_id": pk or request.query_params.get('id')})
      else:
        return get("get_all_tasks", {"job_type": 3})

    def post(self, request, *args, **kwargs):
      account = Account.objects.get(id=request.data["customer_comment"])
      job_delivery_datetime = parse_datetime(request.data["job_delivery_datetime"])
      job_pickup_datetime = parse_datetime(request.data["job_pickup_datetime"])
      new_data = {
          **request.data, 
          **{
            "customer_username": account.name,
            "customer_phone": account.phone or "1234567890",
            "customer_address": account.billing_street,
            "latitude": str(account.billing_latitude),
            "longitude": str(account.billing_longitude),
            "job_delivery_datetime": job_delivery_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "job_pickup_datetime": job_pickup_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "has_pickup": "0",
            "has_delivery": "0",
            "layout_type": "1",
            "tracking_link": 1,
            "auto_assignment": "0",
            "notify": 1,
          } 
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
        return get("get_all_fleets")

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
      return post("customer/add", {
        **request.data, 
        **{
          "user_type": 0, 
          "name": request.data["email"], 
          "phone": randint(1000000000, 9999999999) ,
          }
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
