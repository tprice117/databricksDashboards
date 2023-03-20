from django.apps import AppConfig
from django.conf import settings
import os
import pickle

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'


class MlConfig(AppConfig):    
    path = os.path.join(settings.ML_MODELS, 'models.pkl')
    with open(path, 'rb') as pickled:
       data = pickle.load(pickled)    
    regressor = data['regressor']
    encoder = data['enc']