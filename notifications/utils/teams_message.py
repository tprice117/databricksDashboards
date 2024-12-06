import requests
import logging

logger = logging.getLogger(__name__)


def send_teams_message(
    team_link: str,
    msg_body: str,
    msg_title: str = None,
    board: str = None,
    assigned_to: str = None,
    custom_elements: list = None,
    view_link: str = None,
) -> requests.Response:
    """
    Send a Teams message to the internal team.

    Args:
        team_link (str): The webhook URL for the Microsoft Teams channel.
        msg_body (str): The main message body to be sent.
        msg_title (str, optional): The title of the card. Defaults to None.
        board (str, optional): The name of the board related to the message. Defaults to None.
        assigned_to (str, optional): The name of the person/team the task is assigned to. Defaults to None.
        custom_elements (list, optional): A list of custom elements to be included in the message after the message body.
            Refer to https://adaptivecards.io/explorer/ for more information. Defaults to None.
        view_link (str, optional): A URL to be included as a "View" button in the message. Defaults to None.

    Returns:
        requests.Response: The response from the Microsoft Teams webhook API.
    """
    card_body = []
    card_facts = []

    # Update title
    if msg_title:
        card_body.append(
            {
                "type": "TextBlock",
                "text": msg_title,
                "weight": "bolder",
                "size": "extraLarge",
                "wrap": True,
            }
        )

    # Update facts
    if board:
        card_facts.append(
            {
                "title": "Board:",
                "value": board,
            }
        )
    if assigned_to:
        card_facts.append(
            {
                "title": "Assigned to:",
                "value": assigned_to,
            }
        )

    # Create card body
    card_body.extend(
        [
            {
                "type": "TextBlock",
                "text": msg_body,
                "wrap": True,
            },
            {
                "type": "FactSet",
                "facts": card_facts,
            },
        ]
    )

    if custom_elements:
        card_body.extend(custom_elements)

    # Create card data
    card_data = {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": card_body,
        },
    }

    # Add view link
    if view_link:
        card_data["content"]["actions"] = [
            {
                "type": "Action.OpenUrl",
                "title": "View",
                "url": view_link,
            }
        ]

    # Final payload
    json_data = {
        "type": "message",
        "attachments": [card_data],
    }
    response = requests.post(team_link, json=json_data)
    return response
