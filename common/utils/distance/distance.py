import math

import googlemaps
import numpy as np

GOOGLE_MAPS_API = r"AIzaSyCKjnDJOCuoctPWiTQLdGMqR6MiXc_XKBE"


class DistanceUtils:
    @staticmethod
    def get_driving_distance(lat1, lon1, lat2, lon2, unit="M"):
        """Use google maps api to calculate the driving distance between two points."""
        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API)
        try:
            distance = gmaps.distance_matrix(
                (lat1, lon1), (lat2, lon2), mode="driving"
            )["rows"][0]["elements"][0]["distance"]["value"]
            if unit == "M":
                return distance * 0.000621371
            elif unit == "K":
                return distance * 0.001
            else:
                return distance
        except:
            return np.nan

    @staticmethod
    def get_euclidean_distance(lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)
        """
        lat_a = math.radians(lat1)
        lat_b = math.radians(lat2)
        long_diff = math.radians(float(lon1) - float(lon2))
        distance = math.sin(lat_a) * math.sin(lat_b) + math.cos(lat_a) * math.cos(
            lat_b
        ) * math.cos(long_diff)
        resToMile = math.degrees(math.acos(distance)) * 69.09
        return resToMile
