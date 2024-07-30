from django.db.models.signals import pre_save
from django.dispatch import receiver

from common.middleware.save_author import get_request
from common.models import BaseModel


@receiver(pre_save)
def base_model_pre_save(sender, instance: BaseModel, **kwargs):
    print("Running base_model_pre_save")
    # Sets the 'created_by' and 'updated_by' if 'sender' is a subclass of BaseModel
    if issubclass(sender, BaseModel):

        # Get current user via author backend.
        request = get_request()

        authenticated_user = None
        if hasattr(request, "auth"):
            authenticated_user = request.auth
        elif hasattr(request, "user"):
            authenticated_user = request.user

        # Set the 'updated_by' user.
        instance.updated_by = authenticated_user

        # If creating object, set the 'created_by' field.
        if (
            sender.objects.filter(pk=instance.pk).exists() is False
            and authenticated_user is not None
        ):
            instance.created_by = authenticated_user
