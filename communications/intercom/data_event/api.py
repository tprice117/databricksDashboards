import requests
from django.utils import timezone
from typing import Union, List
import logging
from communications.intercom.utils.utils import IntercomUtils
from communications.intercom.typings import DataEventSummaryType

logger = logging.getLogger(__name__)


class DataEvent:
    @staticmethod
    def all_summaries(intercom_id: str) -> Union[List[DataEventSummaryType], None]:
        """Get all Contact event summaries from Intercom. Intercom only goes back 90 days.
        API spec: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Data-Events/lisDataEvents/

        Args:
            intercom_id (str): User.intercom_id

        Returns:
            Union[List[DataEventSummaryType], None]: Return a list of event summaries on success, else None.
        """
        items = []
        api_params = {"intercom_user_id": intercom_id, "type": "user", "summary": "true"}
        page_url = "https://api.intercom.io/events?per_page=25&page=1"
        while page_url:
            resp = requests.get(page_url, headers=IntercomUtils.headers, params=api_params)
            if resp.status_code >= 400:
                return None
            # Page data.
            resp_data = resp.json()
            for evt in resp_data['events']:
                items.append(DataEventSummaryType(evt))
            page_url = resp_data.get("pages", {}).get("next", None)

        return items

    @staticmethod
    def create(
        intercom_id: str, event_name: str, created_at: int = None, metadata: dict = None
    ) -> bool:
        """Creates a Data Event in Intercom.
        API spec: https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Data-Events/createDataEvent/

        Args:
            intercom_id (str): User.intercom_id
            event_name (str): The name of the event that occurred. This is presented to your App's admins
                              when filtering and creating segments - a good event name is typically a past
                              tense 'verb-noun' combination, to improve readability, for example updated-plan.
            created_at (int): Unix timestamp. Intercom recommends to keep its precision to seconds.
            metadata (dict, optional): Intercom event metadata, similar to Company custom_attributes. Defaults to None.

        Returns:
            bool: Returns True if api completed successfully, else False.
        """
        if created_at is None:
            created_at = int(timezone.now().timestamp())  # Round down to nearest second
        api_params = {
            "id": intercom_id,
            "event_name": event_name,
            "created_at": created_at
        }
        if metadata is not None:
            api_params['metadata'] = metadata
        resp = requests.post(
            "https://api.intercom.io/events",
            headers=IntercomUtils.headers,
            json=api_params,
        )
        if resp.status_code < 400:
            return True
        else:
            logger.error(
                f"DataEvent.create: intercom_id:[{intercom_id}], event_name:[{event_name}], created_at: [{created_at}], response:{resp.status_code}-[{resp.content}]")
            return False
