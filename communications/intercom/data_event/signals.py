from django.db.models.signals import post_save, post_delete
from typing import Union
# import threading
import logging
from api.models import User, UserAddress, Order
from communications import intercom
from communications.intercom.utils.utils import get_json_safe_value

logger = logging.getLogger(__name__)

"""User, UserAddress, and Order track fields needed for the Intercom Events.
If another field needs to be tracked, go to the model class and edit the
track_data class decorator parameters.

Django Signals help: https://docs.djangoproject.com/en/5.0/topics/signals/
"""


def get_updated_metadata(old_data: dict, db_obj: Union[User, UserAddress, Order]) -> dict:
    """Creates a dict with changes for Intercom events.

    Args:
        old_data (dict): Previous data in a dict that has now been updated (from whats_changed())
        db_obj (Union[User, UserAddress, Order]): The database object.

    Returns:
        dict: Changed data in "Updated <key>": val dict e.g. {"Updated phone": "new:[+14048582928] | old:[None]"}
    """
    changes = {}
    for key, val in old_data.items():
        oldval = get_json_safe_value(val)
        newval = get_json_safe_value(getattr(db_obj, key))
        changes[f"Updated {key}"] = f"new:[{newval}] | old:[{oldval}]"
    return changes


def get_tracked_data(db_obj: Union[User, UserAddress, Order]) -> dict:
    """Get tracked data as key:val dictionary. Only retrieve non None data.

    Args:
        db_obj (Union[User, UserAddress, Order]): The database object.

    Returns:
        dict: Non None data in key:val dict.
    """
    data = {}
    for key, val in db_obj.__data.items():
        dbval = get_json_safe_value(getattr(db_obj, key))
        if dbval is not None:
            data[key] = dbval
    return data

# ================================================#
# Intercom events on User database actions
# ================================================#


def on_user_post_save(sender, **kwargs):
    """Sends an Intercom Event with metadata on User database actions:

    CREATE:
    Model ID: UserAddress.id
    Email: User.email
    Also attach any of the tracked fields on User model.

    UPDATE:
    Model ID: UserAddress.id
    Email: User.email

    Monitor data change on the tracked fields on User model:
    email, phone, first_name, last_name, is_archived,
    salesforce_contact_id, salesforce_seller_location_id,
    terms_accepted
    """
    user: User = kwargs.get('instance', None)
    if 'created' in kwargs and kwargs['created']:
        # User Creation
        try:
            # Add Intercom Data Event
            if user.intercom_id is None:
                raise ValueError("intercom_id is None")
            metadata = {
                "Model ID": str(user.id),
                **get_tracked_data(user)
            }
            intercom.DataEvent.create(user.intercom_id, "created-User", metadata=metadata)
        except Exception as e:
            logger.exception(f"on_user_post_save: [created-User][{e}]")
    else:
        # User Modification
        try:
            # Get changed data from tracked_data decorator on User
            changed = user.whats_changed()
            # Only send an event if relevant data has changed.
            if changed:
                metadata = {
                    "Model ID": str(user.id),
                    "Email": user.email,
                    **get_updated_metadata(changed, user)
                }
                intercom.DataEvent.create(user.intercom_id, "updated-User", metadata=metadata)
        except Exception as e:
            logger.exception(f"on_user_post_save: [updated-User]-[{e}]")


# ================================================#
# Intercom events on UserAddress database actions
# ================================================#

def on_user_address_post_save(sender, **kwargs):
    """Sends an Intercom Event with metadata on UserAddress database actions:

    CREATE:
    Model ID: UserAddress.id
    Email: UserAddress.User.email
    Also attach any of the tracked fields on UserAddress model.

    UPDATE:
    Model ID: UserAddress.id
    Email: UserAddress.User.email
    Address: UserAddress.formatted_address()

    Monitor data change on the tracked fields on UserAddress model:
    name, project_id, street, city, state, postal_code, country, access_details, autopay
    """
    useraddress: UserAddress = kwargs.get('instance', None)
    if 'created' in kwargs and kwargs['created']:
        # User Address Creation
        try:
            # Add Intercom Data Event
            if useraddress.user.intercom_id is None:
                raise ValueError("intercom_id is None")
            metadata = {
                "Model ID": str(useraddress.id),
                "Email": useraddress.user.email,
                "Address": useraddress.formatted_address(),
                **get_tracked_data(useraddress)
            }
            intercom.DataEvent.create(useraddress.user.intercom_id, "created-UserAddress", metadata=metadata)
        except Exception as e:
            logger.exception(f"on_user_address_post_save: [{e}]")
    else:
        # User Address Modification
        try:
            # Get changed data from tracked_data decorator on User
            changed = useraddress.whats_changed()
            # Only send an event if relevant data has changed.
            if changed:
                # Previous Address
                metadata = {
                    "Model ID": str(useraddress.id),
                    "Email": useraddress.user.email,
                    "Address": useraddress.formatted_address(),
                    **get_updated_metadata(changed, useraddress)
                }
                intercom.DataEvent.create(useraddress.user.intercom_id, "updated-UserAddress", metadata=metadata)
        except Exception as e:
            logger.exception(f"on_user_address_post_save: [updated-UserAddress]-[{e}]")


def on_user_address_post_delete(sender, **kwargs):
    """Sends an Intercom event with Address on UserAddress database deletion."""
    # Send an Intercom Event with previous address data on User Address deletion.
    useraddress: UserAddress = kwargs.get('instance', None)
    if (useraddress is not None):
        try:
            if useraddress.user.intercom_id is None:
                raise ValueError("intercom_id is None")
            # Previous address data
            metadata = {
                "Model ID": str(useraddress.id),
                "Email": useraddress.user.email,
                "Address": useraddress.formatted_address(),
                **get_tracked_data(useraddress)
            }
            if useraddress.user_address_type:
                metadata["Address"] = f"{useraddress.user_address_type.name}: {metadata['Address']}"
            intercom.DataEvent.create(useraddress.user.intercom_id, "deleted-UserAddress", metadata=metadata)
        except Exception as e:
            logger.exception(f"on_user_address_post_delete:[{e}]")


# ================================================#
# Intercom events on Order database actions
# ================================================#

def on_order_post_save(sender, **kwargs):
    """Sends an Intercom Event with metadata on Order database actions:

    CREATE:
    Model ID: Order.id
    Address Street: Order.OrderGroup.UserAddress.Street
    Product Name: Order.OrderGroup.SellerProductSellerLocation.SellerProduct.Product.MainProduct.Name
    StartDate: Order.StartDate
    EndDate: Order.EndDate

    UPDATE:
    Model ID: Order.id
    Address Street: Order.OrderGroup.UserAddress.Street
    Product Name: Order.OrderGroup.SellerProductSellerLocation.SellerProduct.Product.MainProduct.Name
    StartDate: Order.StartDate
    EndDate: Order.EndDate

    Monitor data change on the tracked fields on UserAddress model:
    submitted_on, start_date, end_date, schedule_details, schedule_window
    """
    order: Order = kwargs.get('instance', None)
    if 'created' in kwargs and kwargs['created']:
        # Order Creation
        if (order is not None):
            try:
                # Add Intercom Data Event
                if order.order_group.user.intercom_id is None:
                    raise ValueError("intercom_id is None")
                metadata = {
                    "Model ID": str(order.id),
                    "StartDate": get_json_safe_value(order.start_date),
                    "EndDate": get_json_safe_value(order.end_date),
                }
                if order.order_group:
                    metadata['Address'] = order.order_group.user_address.formatted_address()
                    metadata['Product Name'] = order.order_group.seller_product_seller_location.seller_product.product.main_product.name
                if order.submitted_on:
                    metadata['Submitted On'] = get_json_safe_value(order.submitted_on)
                if order.schedule_details:
                    metadata['Schedule Details'] = order.schedule_details
                if order.schedule_window:
                    metadata['Schedule Window'] = order.get_schedule_window_display()
                intercom.DataEvent.create(order.order_group.user.intercom_id, "created-Order", metadata=metadata)
            except Exception as e:
                logger.exception(f"on_order_post_save: [created-Order]-[{e}]")
    else:
        # Order updated
        try:
            changed = order.whats_changed()
            if changed and order.submitted_on is not None and order.old_value('submitted_on') is None:
                # Add Intercom Data Event
                if order.order_group.user.intercom_id is None:
                    raise ValueError("intercom_id is None")
                metadata = {
                    "Model ID": str(order.id),
                    **get_tracked_data(order)
                }
                if order.order_group:
                    metadata['Address'] = order.order_group.user_address.formatted_address()
                    metadata['Product Name'] = order.order_group.seller_product_seller_location.seller_product.product.main_product.name
                # Ensure start and end dates are in event, either as current or as updated data.
                if metadata.get("Updated start_date", None) is None:
                    metadata["StartDate"] = get_json_safe_value(order.start_date)
                if metadata.get("Updated end_date", None) is None:
                    metadata["EndDate"] = get_json_safe_value(order.end_date)

                intercom.DataEvent.create(order.order_group.user.intercom_id, "submitted-Order", metadata=metadata)
        except Exception as e:
            logger.exception(f"submit_order: [submitted-Order]-[{e}]")


post_save.connect(on_user_post_save, sender=User)
post_save.connect(on_user_address_post_save, sender=UserAddress)
post_delete.connect(on_user_address_post_delete, sender=UserAddress)
post_save.connect(on_order_post_save, sender=Order)

# def on_user_address_pre_save(sender, **kwargs):
#     if 'created' not in kwargs and kwargs['created']:
#         # User Modification (capture details of what changed, listen for post_save signal on User model)
#         useraddress = kwargs.get('instance', None)
#         if (useraddress is not None):
#             try:
#                 # Add Intercom Data Event
#                 if useraddress.user.intercom_id is None:
#                     raise ValueError("intercom_id is None")
#                 metadata = {
#                     "Model ID": useraddress.user.id,
#                     "email": useraddress.user.email,
#                     "address": useraddress.formatted_address(),
#                     "changes": []
#                 }
#                 prev_address = UserAddress.objects.get(id=useraddress.id)
#                 allfields = [s.name for s in useraddress._meta.fields]
#                 for _field in allfields:
#                     if (_field != 'id'):
#                         old_val = getattr(prev_address, _field)
#                         new_val = getattr(useraddress, _field)
#                         if (old_val != new_val):
#                             metadata['changes'].append({'old': old_val, 'new': new_val})
#                 intercom.DataEvent.create(useraddress.intercom_id, "updated-UserAddress", metadata=metadata)
#             except Exception as e:
#                 logger.exception(f"on_user_address_pre_save: [{e}]")
