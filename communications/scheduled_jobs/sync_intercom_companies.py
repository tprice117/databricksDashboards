from api.models.user.user_group import UserGroup
from api.models.user.user import User
from communications.intercom.intercom import Intercom


def sync_intercom_companies():
    """
    Synchronizes User Groups with Intercom Companies.
    Creates new Companies and deletes ones that are no longer
    present in the database.
    """
    # Skip this if not in "TEST" mode.
    # if settings.ENVIRONMENT != "TEST":
    #     return

    print("Syncing Intercom Companies...")

    # # Get latest data from Intercom.
    # companies = Intercom.Company.all()

    # # Get latest list of UserGroups.
    # user_groups = UserGroup.objects.all()

    # # Delete Companies that are no longer present in the database.
    # existing_ids = {company["company_id"] for company in companies}
    # deleted_ids = existing_ids - {str(user_group.id) for user_group in user_groups}
    # for deleted_id in deleted_ids:
    #     Intercom.Company.delete(company_id=deleted_id)

    # # Update or create Companies.
    # for user_group in user_groups:
    #     if str(user_group.id) in existing_ids:
    #         # If the Company already exists, update it.
    #         Intercom.Company.update(
    #             company_id=str(user_group.id),
    #             name=user_group.name,
    #         )
    #     else:
    #         # If the Company does not exist, create it.
    #         Intercom.Company.create(
    #             company_id=str(user_group.id),
    #             name=user_group.name,
    #         )

    # Sync Users to Companies.
    # attach_users_to_companies()


def attach_users_to_companies(_debug=False):
    """
    Attach Users to Companies in Intercom.
    This will also delete companies in Intercom that are no longer present in the Downstream database.
    """
    # Get all UserGroups (UserGroups are called Companies in Intercom).
    user_groups = UserGroup.objects.all()
    # Get all Intercom Companies.
    companies = Intercom.Company.all()

    # Loop all UserGroups and create or update Companies in Intercom.
    for user_group in user_groups:
        company = user_group.intercom_sync()
        if company:
            # Delete company from companies dictionary
            if company["id"] in companies:
                del companies[company["id"]]

    # Delete companies in Intercom that are no longer present in the Downstream database.
    for company in companies.values():
        Intercom.Company.delete(company["id"])

    # Get all users from the UserGroup.
    # Loop all users and create/update info in Intercom
    users = User.objects.all()
    for user in users:
        user.intercom_sync()
