from rest_framework import serializers


class OrderRescheduleRequestSerializer(serializers.Serializer):
    date = serializers.DateField(required=True)


class OrderScheduleWindowRequestSerializer(serializers.Serializer):
    schedule_window = serializers.ChoiceField(
        default="Anytime (7am-4pm)",
        choices=["Anytime (7am-4pm)", "Morning (7am-11am)", "Afternoon (12pm-4pm)"],
    )
