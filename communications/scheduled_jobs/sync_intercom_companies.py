from django.conf import settings
from intercom.client import Client

from api.models.user.user_group import UserGroup
from communications.intercom.intercom import Intercom


def sync_intercom_companies():
    """
    Synchronizes User Groups with Intercom Companies.
    Creates new Companies and deletes ones that are no longer
    present in the database.
    """
    # Skip this if not in "TEST" mode.
    if settings.ENVIRONMENT != "TEST":
        return

    intercom = Client(
        personal_access_token=settings.INTERCOM_ACCESS_TOKEN,
    )
    print("Syncing Intercom Companies...")

    # Get latest data from Intercom.
    companies = Intercom.Company.all()
    print("Companies:", companies)
    for company in companies:
        print(str(company))

    # Get latest list of UserGroups.
    user_groups = UserGroup.objects.all()

    # Delete Companies that are no longer present in the database.
    existing_ids = {company["company_id"] for company in companies}
    deleted_ids = existing_ids - {str(user_group.id) for user_group in user_groups}
    for deleted_id in deleted_ids:
        Intercom.Company.delete(company_id=deleted_id)

    # Update or create Companies.
    for user_group in user_groups:
        if str(user_group.id) in existing_ids:
            # If the Company already exists, update it.
            Intercom.Company.update(
                company["company_id"],
                name=user_group.name,
            )
        else:
            # If the Company does not exist, create it.
            Intercom.Company.create(
                company_id=str(user_group.id),
                name=user_group.name,
            )
