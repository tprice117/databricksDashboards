from rest_framework import serializers


class OrderGroupNewTransactionRequestSerializer(serializers.Serializer):
    date = serializers.DateField(required=True)
    schedule_window = serializers.ChoiceField(
        default="Anytime (7am-4pm)",
        choices=["Anytime (7am-4pm)", "Morning (7am-11am)", "Afternoon (12pm-4pm)"],
    )


class OrderGroupAccessDetailsRequestSerializer(serializers.Serializer):
    access_details = serializers.CharField(required=True)


class OrderGroupPlacementDetailsRequestSerializer(serializers.Serializer):
    placement_details = serializers.CharField(required=True)
    delivered_to_street = serializers.CharField(required=True)
