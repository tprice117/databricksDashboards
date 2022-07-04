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

# To DO: Create GET, POST, PUT general methods.

stripe.api_key = settings.STRIPE_SECRET_KEY
baseUrl = "https://api.thetrashgurus.com/v2/"
MAX_RETRIES = 5
API_KEY = '556b608df7434e42464e753f4313254019e2c1f328da783b541505'

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

def get(endpoint):
  url =  baseUrl + endpoint
  payload = {"api_key": API_KEY}
  return call_TG_API(url, payload)

def post(endpoint, body):
  url =  baseUrl + endpoint
  payload = {"api_key": API_KEY} | body
  return call_TG_API(url, payload)

def put(endpoint, body):
  url =  baseUrl + endpoint
  payload = {"api_key": API_KEY} | body
  return call_TG_API(url, payload)

def delete(endpoint, body):
  url =  baseUrl + endpoint
  payload = {"api_key": API_KEY} | body
  return call_TG_API(url, payload)



class TaskView(APIView):
    def get(self, request, pk=None, *args, **kwargs):  
      if pk or request.query_params.get('id'):   
        return post("get_job_details_by_order_id", {"order_id": pk or request.query_params.get('id')})
      else:
        return get("get_all_tasks")

    def post(self, request, *args, **kwargs):
      return post("create_task", request.data)

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
        return get("view_all_team_only")

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
        return get("get_all_customers")

    def post(self, request, *args, **kwargs):
      return post("customer/add", request.data | {"user_type": 0})

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
