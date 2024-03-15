from django.test import TestCase
from api.models.user.user_group import UserGroup
from api.models.user.user import User
from communications.intercom.contact import Contact
from communications.intercom.company import Company
import uuid
import time


class IntercomTests(TestCase):

    def test_intercom_db(self):
        # Save a UserGroup
        test_id = str(uuid.uuid4())
        name = f"test_{test_id}"
        email = f"test_{test_id}@test.com"

        usergroup = UserGroup.objects.create(name=name)
        time.sleep(2)
        usergroup = UserGroup.objects.get(id=usergroup.id)
        self.assertIsNotNone(usergroup.intercom_id)

        # Save a User
        user = User.objects.create(email=email, user_group=usergroup)
        time.sleep(2)
        user = User.objects.get(id=user.id)
        self.assertIsNotNone(user.intercom_id)

        # Check if UserGroup is in Intercom
        company = Company.get(usergroup.intercom_id)
        self.assertIsNotNone(company)
        contact = Contact.get(user.intercom_id)
        self.assertIsNotNone(contact)

        # Delete User
        user.delete()
        contact = Contact.get(user.intercom_id)
        self.assertIsNone(contact)

        # Delete UserGroup
        usergroup.delete()

    def test_intercom(self):
        contact = None
        company = None
        test_id = str(uuid.uuid4())
        downstream_usergroup_id = f"{test_id}_company_id"
        company_name = f"{test_id} Trash Panda"
        downstream_user_id = f"{test_id}"
        email = f"{test_id}@domain.com"
        name = f"{test_id} Michael Wickey"
        # Create a contact in Intercom.
        contact = Contact.create(
            downstream_user_id,
            f"typo_{email}",
            name=name
        )
        self.assertIsNotNone(contact)

        # test_intercom_update_contact
        # Update a contact in Intercom.
        contact = Contact.update(contact["id"], downstream_user_id, email, name=name)
        self.assertIsNotNone(contact)
        self.assertEqual(contact["email"], email)

        # test_intercom_search_by_email
        # Get contact from email
        contact = Contact.search_by_email(
            email=email,
        )
        self.assertIsNotNone(contact)

        no_contact = Contact.search_by_email(
            email=f"typo_{email}",
        )
        self.assertIsNone(no_contact)

        # test_update_or_create_company
        company = Company.update_or_create(downstream_usergroup_id, f"typo_{company_name}")
        self.assertIsNotNone(company)

        company = Company.update_or_create(downstream_usergroup_id, company_name)
        self.assertEqual(company["name"], company_name)

        # test_get_company
        no_company = Company.get(f'{company["id"]}_doesnotexist')
        self.assertIsNone(no_company)

        company = Company.get(company["id"])
        self.assertIsNotNone(company)

        # test_attach_user_to_company
        # Attach a User to a Company in Intercom.
        company = Contact.attach_user(company["id"], contact["id"])
        self.assertIsNotNone(company)

        # Attach a User to a Company in Intercom again to test.
        company = Contact.attach_user(company["id"], contact["id"])
        self.assertIsNotNone(company)

        # test_delete_contact
        # Delete a contact from Intercom. contact['id']
        del_contact = Contact.delete(contact["id"])
        self.assertIsNotNone(del_contact)
        self.assertTrue(del_contact["deleted"])

        # test_delete_company
        # Delete a company from Intercom. company['company_id']
        del_company = Company.delete(company["id"])
        self.assertIsNotNone(del_company)
        self.assertTrue(del_company["deleted"])
