from rest_framework import serializers


class OrderRescheduleRequestSerializer(serializers.Serializer):
    date = serializers.DateField(required=True)
