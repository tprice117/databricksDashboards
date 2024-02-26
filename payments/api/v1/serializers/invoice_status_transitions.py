from rest_framework import serializers


class InvoiceStatusTransitionSerializer(serializers.Serializer):
    finalized_at = serializers.DateTimeField(read_only=True)
    marked_uncollectible_at = serializers.DateTimeField(read_only=True)
    paid_at = serializers.DateTimeField(read_only=True)
    voided_at = serializers.DateTimeField(read_only=True)
