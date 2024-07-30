import requests
from typing import Dict, List, Union, Literal
import logging
from django.utils import timezone
from enum import Enum

from communications.intercom.utils.utils import IntercomUtils

logger = logging.getLogger(__name__)


class Conversation:

    ADMIN_ID = "7376407"  # Danica

    class Tags(Enum):
        BOOKING = "7634085"
        CUSTOMER = "7634175"
        SELLER = "7634177"

    @staticmethod
    def parse_conversation(conversation_data: dict, user_intercom_id: str):
        conversation = [
            {
                "author": conversation_data["source"]["author"]["name"],
                "body": conversation_data["source"]["body"],
                "created_at": timezone.datetime.fromtimestamp(
                    conversation_data["created_at"], tz=timezone.utc
                ),
                "is_admin": conversation_data["source"]["author"]["type"] == "admin",
                "sent_by_current_user": conversation_data["source"]["author"]["id"]
                == user_intercom_id,
            }
        ]
        for part in conversation_data["conversation_parts"]["conversation_parts"]:
            if (
                part["part_type"] == "comment"
                or (
                    part["body"]
                    and (part["part_type"] == "open" or part["part_type"] == "close")
                )
            ) and not part["redacted"]:
                resp = {
                    "author": part["author"]["name"],
                    "body": part["body"],
                    "created_at": timezone.datetime.fromtimestamp(
                        part["created_at"], tz=timezone.utc
                    ),
                    "is_admin": part["author"]["type"] == "admin",
                    "sent_by_current_user": part["author"]["id"] == user_intercom_id,
                }
                conversation.append(resp)
        # print(f"{user.email}: read {conversation_data['read']}")
        return conversation

    @staticmethod
    def send_message(user_intercom_id: str, subject: str, message: str):
        """Begin conversation with a user.
        https://developers.intercom.com/docs/references/rest-api/api.intercom.io/messages/createmessage
        """
        payload = {
            "message_type": "email",  # in_app, email
            "subject": subject,
            "body": message,
            "template": "personal",  # personal, plain
            "from": {"type": "admin", "id": Conversation.ADMIN_ID},
            "to": {"type": "user", "id": user_intercom_id},
            "create_conversation_without_contact_reply": True,
        }
        msgurl = "https://api.intercom.io/messages"
        response = requests.post(msgurl, json=payload, headers=IntercomUtils.headers)

        if response.status_code < 400:
            return response.json()
        else:
            logger.error(
                f"Conversation.send_message: user_intercom_id:[{user_intercom_id}], subject:[{subject}], message:[{message}], response:{response.status_code}-[{response.content}]"
            )

    @staticmethod
    def attach_tag(conversation_id: str, tag_id: str):
        """Attach tag to a conversation.
        https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/attachtagtoconversation
        """
        tagurl = "https://api.intercom.io/conversations/" + conversation_id + "/tags"
        payload = {"id": tag_id, "admin_id": Conversation.ADMIN_ID}
        response = requests.post(tagurl, json=payload, headers=IntercomUtils.headers)

        if response.status_code < 400:
            return response.json()
        else:
            logger.error(
                f"Conversation.send_message: conversation_id:[{conversation_id}], tag_id:[{tag_id}], response:{response.status_code}-[{response.content}]"
            )

    @staticmethod
    def attach_booking_tag(conversation_id: str):
        return Conversation.attach_tag(conversation_id, Conversation.Tags.BOOKING.value)

    @staticmethod
    def get(conversation_id: str, user_intercom_id: str, plain=False):
        # https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/retrieveconversation
        get_conversation_url = (
            f"https://api.intercom.io/conversations/{conversation_id}"
        )
        query = {}
        if plain:
            query["display_as"] = "plaintext"
        response = requests.get(
            get_conversation_url, headers=IntercomUtils.headers, params=query
        )
        if response.status_code < 400:
            conversation_data = response.json()
            conversation = Conversation.parse_conversation(
                conversation_data, user_intercom_id
            )
            return conversation
        else:
            logger.error(
                f"Conversation.get: conversation_id:[{conversation_id}], response:{response.status_code}-[{response.content}]"
            )

    @staticmethod
    def reply(conversation_id: str, user_intercom_id: str, message: str, plain=False):
        """Reply to a conversation from a user.
        https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/replyconversation
        """
        payload = {
            "intercom_user_id": user_intercom_id,
            "message_type": "comment",
            "type": "user",
            "body": message,
        }
        if plain:
            payload["display_as"] = "plaintext"

        conversation_url = (
            "https://api.intercom.io/conversations/" + conversation_id + "/reply"
        )
        response = requests.post(
            conversation_url, headers=IntercomUtils.headers, json=payload
        )

        if response.status_code < 400:
            conversation_data = response.json()
            conversation = Conversation.parse_conversation(
                conversation_data, user_intercom_id
            )
            return conversation
        else:
            logger.error(
                f"Conversation.reply: conversation_id:[{conversation_id}], user_intercom_id:[{user_intercom_id}], response:{response.status_code}-[{response.content}]"
            )

    @staticmethod
    def admin_reply(
        conversation_id: str, user_intercom_id: str, message: str, plain=False
    ):
        """Reply to a conversation from an admin.
        https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/replyconversation
        """
        payload = {
            "admin_id": Conversation.ADMIN_ID,
            "message_type": "comment",
            "type": "admin",
            "body": message,
        }
        if plain:
            payload["display_as"] = "plaintext"

        conversation_url = (
            "https://api.intercom.io/conversations/" + conversation_id + "/reply"
        )
        response = requests.post(
            conversation_url, headers=IntercomUtils.headers, json=payload
        )

        if response.status_code < 400:
            conversation_data = response.json()
            conversation = Conversation.parse_conversation(
                conversation_data, user_intercom_id
            )
            return conversation
        else:
            logger.error(
                f"Conversation.reply: conversation_id:[{conversation_id}], user_intercom_id:[{user_intercom_id}], response:{response.status_code}-[{response.content}]"
            )

    @staticmethod
    def admin_read(conversation_id: str, user_intercom_id: str, plain=False):
        """Sets the conversation as read by the admin.
        NOTE: Read, currently, only has significance for admins in Intercom.
        https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/updateconversation
        """
        # TODO: Call htmx onload to view the conversation.
        get_conversation_url = (
            f"https://api.intercom.io/conversations/{conversation_id}"
        )
        payload = {
            "read": True,
        }
        response = requests.put(
            get_conversation_url, json=payload, headers=IntercomUtils.headers
        )
        if response.status_code < 400:
            return response.json()
        else:
            logger.error(
                f"Conversation.admin_read: conversation_id:[{conversation_id}], response:{response.status_code}-[{response.content}]"
            )

    @staticmethod
    def close(conversation_id: str, message: str = None):
        """Close the conversation.
        https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/manageconversation
        """
        url = "https://api.intercom.io/conversations/" + conversation_id + "/parts"
        payload = {
            "message_type": "close",
            "type": "admin",
            "admin_id": Conversation.ADMIN_ID,
        }
        if message:
            payload["body"] = message
        response = requests.post(url, json=payload, headers=IntercomUtils.headers)
        if response.status_code < 400:
            return response.json()
        else:
            logger.error(
                f"Conversation.close: conversation_id:[{conversation_id}], response:{response.status_code}-[{response.content}]"
            )

    @staticmethod
    def attach_users_conversation(user_intercom_ids: List[str], conversation_id: str):
        """Attach users to a conversation.
        https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/attachcontacttoconversation
        """
        csturl = (
            "https://api.intercom.io/conversations/" + conversation_id + "/customers"
        )
        payload = {"admin_id": Conversation.ADMIN_ID}
        for intercom_id in user_intercom_ids:
            payload["customer"] = {"intercom_user_id": intercom_id}
            response = requests.post(
                csturl, json=payload, headers=IntercomUtils.headers
            )
            # data = response.json()
            if response.status_code >= 400:
                logger.error(
                    f"Conversation.attach_users_conversation: user intercom_id:[{intercom_id}], conversation_id:[{conversation_id}], response:{response.status_code}-[{response.content}]"
                )

    @staticmethod
    def detach_users_conversation(user_intercom_ids: List[str], conversation_id: str):
        """Detach users from a conversation.
        https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/detachcontactfromconversation
        """
        payload = {"admin_id": Conversation.ADMIN_ID}
        for intercom_id in user_intercom_ids:
            url = (
                "https://api.intercom.io/conversations/"
                + conversation_id
                + "/customers/"
                + intercom_id
            )
            payload["customer"] = {"intercom_user_id": intercom_id}
            response = requests.delete(url, json=payload, headers=IntercomUtils.headers)
            # data = response.json()
            if response.status_code >= 400:
                logger.error(
                    f"Conversation.attach_users_conversation: user intercom_id:[{intercom_id}], conversation_id:[{conversation_id}], response:{response.status_code}-[{response.content}]"
                )
