from rest_framework.decorators import api_view
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

@api_view(["GET","POST","PUT"])
def Task(request):
  if request.method == "GET":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "get_all_tasks"
        payload = {"api_key": API_KEY}
        response = requests.post(url, data = payload)
        if response.status_code == 200:
            data = response.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "POST":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "add_agent"
        payload = BASE_PAYLOAD.extend({
          "email": "testAPIemail@test.com"
        })
        response = requests.post(url, data = payload)
        if r.status_code == 200:
            data = r.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "PUT":
      attempt_num = 0  # keep track of how many times we've retried
      while attempt_num < MAX_RETRIES:
          url = 'www.apiexternal.com/endpoint'
          payload = {'Token':'My_Secret_Token','product':'product_select_in_form','price':'price_selected_in_form'}
          response = requests.post(url, data = payload)
          if r.status_code == 200:
              data = r.json()
              return Response(data, status=status.HTTP_200_OK)
          else:
              attempt_num += 1
              # You can probably use a logger to log the error here
              time.sleep(5)  # Wait for 5 seconds before re-trying
      return Response({"error": "Request failed"}, status=r.status_code)
  else:
    return Response({"error": "Method not allowed"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET","POST","PUT"])
def Agent(request):
  if request.method == "GET":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "get_all_fleets"
        payload = {"api_key": API_KEY}
        response = requests.post(url, data = payload)
        if response.status_code == 200:
            data = response.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "POST":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "add_agent"
        payload = BASE_PAYLOAD.extend({
          "email": "testAPIemail@test.com"
        })
        response = requests.post(url, data = payload)
        if r.status_code == 200:
            data = r.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "PUT":
      attempt_num = 0  # keep track of how many times we've retried
      while attempt_num < MAX_RETRIES:
          url = 'www.apiexternal.com/endpoint'
          payload = {'Token':'My_Secret_Token','product':'product_select_in_form','price':'price_selected_in_form'}
          response = requests.post(url, data = payload)
          if r.status_code == 200:
              data = r.json()
              return Response(data, status=status.HTTP_200_OK)
          else:
              attempt_num += 1
              # You can probably use a logger to log the error here
              time.sleep(5)  # Wait for 5 seconds before re-trying
      return Response({"error": "Request failed"}, status=r.status_code)
  else:
    return Response({"error": "Method not allowed"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET","POST","PUT"])
def Team(request):
  if request.method == "GET":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "view_all_team_only"
        payload = {"api_key": API_KEY}
        response = requests.post(url, data = payload)
        if response.status_code == 200:
            data = response.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "POST":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "add_agent"
        payload = BASE_PAYLOAD.extend({
          "email": "testAPIemail@test.com"
        })
        response = requests.post(url, data = payload)
        if r.status_code == 200:
            data = r.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "PUT":
      attempt_num = 0  # keep track of how many times we've retried
      while attempt_num < MAX_RETRIES:
          url = 'www.apiexternal.com/endpoint'
          payload = {'Token':'My_Secret_Token','product':'product_select_in_form','price':'price_selected_in_form'}
          response = requests.post(url, data = payload)
          if r.status_code == 200:
              data = r.json()
              return Response(data, status=status.HTTP_200_OK)
          else:
              attempt_num += 1
              # You can probably use a logger to log the error here
              time.sleep(5)  # Wait for 5 seconds before re-trying
      return Response({"error": "Request failed"}, status=r.status_code)
  else:
    return Response({"error": "Method not allowed"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET","POST","PUT"])
def Manager(request):
  if request.method == "GET":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "view_all_manager"
        payload = {"api_key": API_KEY}
        response = requests.post(url, data = payload)
        if response.status_code == 200:
            data = response.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "POST":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "add_agent"
        payload = BASE_PAYLOAD.extend({
          "email": "testAPIemail@test.com"
        })
        response = requests.post(url, data = payload)
        if r.status_code == 200:
            data = r.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "PUT":
      attempt_num = 0  # keep track of how many times we've retried
      while attempt_num < MAX_RETRIES:
          url = 'www.apiexternal.com/endpoint'
          payload = {'Token':'My_Secret_Token','product':'product_select_in_form','price':'price_selected_in_form'}
          response = requests.post(url, data = payload)
          if r.status_code == 200:
              data = r.json()
              return Response(data, status=status.HTTP_200_OK)
          else:
              attempt_num += 1
              # You can probably use a logger to log the error here
              time.sleep(5)  # Wait for 5 seconds before re-trying
      return Response({"error": "Request failed"}, status=r.status_code)
  else:
    return Response({"error": "Method not allowed"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET","POST","PUT"])
def Customer(request):
  if request.method == "GET":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "get_all_customers"
        payload = {"api_key": API_KEY}
        response = requests.post(url, data = payload)
        if response.status_code == 200:
            data = response.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "POST":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "add_agent"
        payload = BASE_PAYLOAD.extend({
          "email": "testAPIemail@test.com"
        })
        response = requests.post(url, data = payload)
        if r.status_code == 200:
            data = r.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "PUT":
      attempt_num = 0  # keep track of how many times we've retried
      while attempt_num < MAX_RETRIES:
          url = 'www.apiexternal.com/endpoint'
          payload = {'Token':'My_Secret_Token','product':'product_select_in_form','price':'price_selected_in_form'}
          response = requests.post(url, data = payload)
          if r.status_code == 200:
              data = r.json()
              return Response(data, status=status.HTTP_200_OK)
          else:
              attempt_num += 1
              # You can probably use a logger to log the error here
              time.sleep(5)  # Wait for 5 seconds before re-trying
      return Response({"error": "Request failed"}, status=r.status_code)
  else:
    return Response({"error": "Method not allowed"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET","POST","PUT"])
def User(request):
  if request.method == "GET":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "get_all_fleets"
        payload = {"api_key": API_KEY}
        response = requests.post(url, data = payload)
        if response.status_code == 200:
            data = response.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "POST":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "add_agent"
        payload = BASE_PAYLOAD.extend({
          "email": "testAPIemail@test.com"
        })
        response = requests.post(url, data = payload)
        if r.status_code == 200:
            data = r.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "PUT":
      attempt_num = 0  # keep track of how many times we've retried
      while attempt_num < MAX_RETRIES:
          url = 'www.apiexternal.com/endpoint'
          payload = {'Token':'My_Secret_Token','product':'product_select_in_form','price':'price_selected_in_form'}
          response = requests.post(url, data = payload)
          if r.status_code == 200:
              data = r.json()
              return Response(data, status=status.HTTP_200_OK)
          else:
              attempt_num += 1
              # You can probably use a logger to log the error here
              time.sleep(5)  # Wait for 5 seconds before re-trying
      return Response({"error": "Request failed"}, status=r.status_code)
  else:
    return Response({"error": "Method not allowed"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET","POST","PUT"])
def Merchant(request):
  if request.method == "GET":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "get_all_fleets"
        payload = {"api_key": API_KEY}
        response = requests.post(url, data = payload)
        if response.status_code == 200:
            data = response.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "POST":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "add_agent"
        payload = BASE_PAYLOAD.extend({
          "email": "testAPIemail@test.com"
        })
        response = requests.post(url, data = payload)
        if r.status_code == 200:
            data = r.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "PUT":
      attempt_num = 0  # keep track of how many times we've retried
      while attempt_num < MAX_RETRIES:
          url = 'www.apiexternal.com/endpoint'
          payload = {'Token':'My_Secret_Token','product':'product_select_in_form','price':'price_selected_in_form'}
          response = requests.post(url, data = payload)
          if r.status_code == 200:
              data = r.json()
              return Response(data, status=status.HTTP_200_OK)
          else:
              attempt_num += 1
              # You can probably use a logger to log the error here
              time.sleep(5)  # Wait for 5 seconds before re-trying
      return Response({"error": "Request failed"}, status=r.status_code)
  else:
    return Response({"error": "Method not allowed"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET","POST","PUT"])
def Mission(request):
  if request.method == "GET":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "get_mission_list"
        payload = {  
          "api_key": API_KEY,
          "start_date":"1900-01-01",
          "end_date":"2999-12-31"
        }
        response = requests.post(url, data = payload)
        if response.status_code == 200:
            data = response.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "POST":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "add_agent"
        payload = BASE_PAYLOAD.extend({
          "email": "testAPIemail@test.com"
        })
        response = requests.post(url, data = payload)
        if r.status_code == 200:
            data = r.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "PUT":
      attempt_num = 0  # keep track of how many times we've retried
      while attempt_num < MAX_RETRIES:
          url = 'www.apiexternal.com/endpoint'
          payload = {'Token':'My_Secret_Token','product':'product_select_in_form','price':'price_selected_in_form'}
          response = requests.post(url, data = payload)
          if r.status_code == 200:
              data = r.json()
              return Response(data, status=status.HTTP_200_OK)
          else:
              attempt_num += 1
              # You can probably use a logger to log the error here
              time.sleep(5)  # Wait for 5 seconds before re-trying
      return Response({"error": "Request failed"}, status=r.status_code)
  else:
    return Response({"error": "Method not allowed"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET","POST","PUT"])
def Geofence(request):
  if request.method == "GET":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "get_all_fleets"
        payload = {"api_key": API_KEY}
        response = requests.post(url, data = payload)
        if response.status_code == 200:
            data = response.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "POST":
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        url =  baseUrl + "add_agent"
        payload = BASE_PAYLOAD.extend({
          "email": "testAPIemail@test.com"
        })
        response = requests.post(url, data = payload)
        if r.status_code == 200:
            data = r.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=r.status_code)
  elif request.method == "PUT":
      attempt_num = 0  # keep track of how many times we've retried
      while attempt_num < MAX_RETRIES:
          url = 'www.apiexternal.com/endpoint'
          payload = {'Token':'My_Secret_Token','product':'product_select_in_form','price':'price_selected_in_form'}
          response = requests.post(url, data = payload)
          if r.status_code == 200:
              data = r.json()
              return Response(data, status=status.HTTP_200_OK)
          else:
              attempt_num += 1
              # You can probably use a logger to log the error here
              time.sleep(5)  # Wait for 5 seconds before re-trying
      return Response({"error": "Request failed"}, status=r.status_code)
  else:
    return Response({"error": "Method not allowed"}, status=status.HTTP_400_BAD_REQUEST)