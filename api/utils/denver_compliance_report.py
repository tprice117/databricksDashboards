import datetime
from django.conf import settings
from api.models import Order, OrderDisposalTicket, UserAddress
import mailchimp_transactional as MailchimpTransactional
from mailchimp_transactional.api_client import ApiClientError
from django.template.loader import render_to_string


def send_denver_compliance_report(user_address_id, user_email):
    user_address = UserAddress.objects.get(pk=user_address_id)
    orders = Order.objects.filter(user_address=user_address)
    order_disposal_tickets = OrderDisposalTicket.objects.filter(order__in=orders)
    print(order_disposal_tickets)

    # Create header object.
    header_objects = {
        "applicant_name": user_address.user_group.name if user_address.user_group else "",
        "project_address": user_address.street,
        "permit_number": "N/A",
        "phone": "000-000-0000",
        "date_completed": datetime.datetime.now().strftime("%m/%d/%Y"),
    }

    # Create array for disposal tickets.
    order_disposal_tickets_inputs = []
    for ticket in order_disposal_tickets:
        order_disposal_tickets_inputs.append({
            "date": ticket.created_on.strftime("%m/%d/%Y"),
            "weight_ticket_id": ticket.ticket_id,
            "landfill": str(ticket.weight) if ticket.waste_type.name == "Trash (Household Goods)" else "",
            "wood": str(ticket.weight) if ticket.waste_type.name == "Wood" else "",
            "concrete_brick_block": str(ticket.weight) if ticket.waste_type.name == "Concrete (No metal)" else "",
            "asphalt": str(ticket.weight) if ticket.waste_type.name == "Asphalt" else "",
            "metal": str(ticket.weight) if ticket.waste_type.name == "Mixed Metal" else "",
            "cardboard": str(ticket.weight) if ticket.waste_type.name == "Cardboard" else "",
            "donation_reuse": str(ticket.weight) if ticket.waste_type.name == "Salvage for Donation/Reuse" else "",
            "other": "",
            "total_diversion": str(ticket.weight) if ticket.waste_type.name != "Trash (Household Goods)" else "0",
            "total_cd_debris": str(ticket.weight),
            "hauler": ticket.order.seller_product_seller_location.seller_location.seller.name,
            "destination": ticket.disposal_location.name,
        })

    # Create object for totals.
    total_diversion = order_disposal_tickets.exclude(
        waste_type__name="Trash (Household Goods)").aggregate(Sum('weight'))['weight__sum']
    total_cd_debris = order_disposal_tickets.aggregate(Sum('weight'))['weight__sum']
    totals = {
        "landfill": order_disposal_tickets.filter(waste_type__name="Trash (Household Goods)").aggregate(Sum('weight'))['weight__sum'] or "0",
        "wood": order_disposal_tickets.filter(waste_type__name="Wood").aggregate(Sum('weight'))['weight__sum'] or "0",
        "concrete_brick_block": order_disposal_tickets.filter(waste_type__name="Concrete (No metal)").aggregate(Sum('weight'))['weight__sum'] or "0",
        "asphalt": order_disposal_tickets.filter(waste_type__name="Asphalt").aggregate(Sum('weight'))['weight__sum'] or "0",
        "metal": order_disposal_tickets.filter(waste_type__name="Mixed Metal").aggregate(Sum('weight'))['weight__sum'] or "0",
        "cardboard": order_disposal_tickets.filter(waste_type__name="Cardboard").aggregate(Sum('weight'))['weight__sum'] or "0",
        "donation_reuse": order_disposal_tickets.filter(waste_type__name="Salvage for Donation/Reuse").aggregate(Sum('weight'))['weight__sum'] or "0",
        "other": "0",
        "total_diversion": total_diversion,
        "total_cd_debris": total_cd_debris,
        "project_diversion_rate": round(100 * float(total_diversion) / float(total_cd_debris), 2) if total_cd_debris else 0,
    }

    mailchimp = MailchimpTransactional.Client(settings.MAILCHIMP_API_KEY)
    response = mailchimp.messages.send({"message": {
        "from_name": "Downstream",
        "from_email": "hello@trydownstream.com",
        "to": [
            {
                "email": user_email,
            },
            {
                "email": "thayes@trydownstream.com"
            }
        ],
        "subject": "Waste Compliance Report Export",
        "track_opens": True,
        "track_clicks": True,
        "html": render_to_string(
            'denver-compliance-form.html',
            {
                "order_disposal_tickets_inputs": order_disposal_tickets_inputs,
                "header_objects": header_objects,
                "totals": totals,
            }
        ),
        # "attachments": [
        #    {
        #         "type": "text/csv",
        #         "name": "waste_compliance_report.csv",
        #         "content": base64.b64encode(csv).decode("utf-8"),
        #    }
        # ]
    }})
    print(response)
