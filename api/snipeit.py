"""
Snipe-IT API module

Module to communicate with defined Snipe-IT instance.
Requires snipeit.conf JSON file within the same directory.
"""
import json
import logging
import os
import sys

from .shared import APIException, contact_api

logger = logging.getLogger(__name__)


class SnipeITAPIException(Exception):
    """Expection for the Snipe-IT API module"""


# Configure SnipeIT API module
try:
    with open(os.path.join(sys.path[0], "api", "snipeit.conf")) as jfile:
        config = json.load(jfile)

        snipeit_url = config.get("url")
        if not snipeit_url:
            raise SnipeITAPIException("Configuration file is missing 'url'")

        token = config.get("token")
        if not token:
            raise SnipeITAPIException("Configuration file is missing 'token'")

        attempts = config.get("attempts", 5)

except SnipeITAPIException:
    raise
except FileNotFoundError:
    raise SnipeITAPIException("Configuration file 'snipeit.conf' is missing")
except Exception:
    raise SnipeITAPIException("Error reading 'snipeit.conf' configuration file")


api_endpoint = f"{snipeit_url}/api/v1"
headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}


def get_data_from_api(url):
    """Return rows of date from API"""
    try:
        data = contact_api(url, headers)
    except APIException as ex:
        raise SnipeITAPIException(ex)
    rows = data.get("rows", None)

    if rows is None:
        raise SnipeITAPIException("Unexpected API response. Missing rows array")
    elif not rows:  # Correct response but no assent found
        return None

    return rows


def get_single_item_from_api(url):
    """Return single item via API or fail"""
    rows = get_data_from_api(url)

    if rows:
        if len(rows) > 1:
            raise SnipeITAPIException(
                "Unexpected API response. Multiple objects with the same identfier."
            )
        else:
            return rows[0]

    return None


def checkout(asset_id, user_id, asset_name=None):
    """Assign user to the asset"""

    logger.info(f"Checking out asset: {asset_id} to user: {user_id}")

    url = f"{api_endpoint}/hardware/{asset_id}/checkout"
    payload = {"checkout_to_type": "user", "assigned_user": user_id}
    if asset_name:
        payload["name"] = asset_name

    try:
        response = contact_api(url, headers, payload=payload, operation="POST")
    except APIException as ex:
        raise SnipeITAPIException(ex)

    if response.get("status") == "success":
        return True

    messages = response.get("messages", "Unknown error")
    logger.error(f"API returner error response: {messages}")
    return False


def checkin(asset_id):
    """Unassign user from the asset"""

    logger.info(f"Checking in asset: {asset_id}")

    url = f"{api_endpoint}/hardware/{asset_id}/checkin"

    try:
        response = contact_api(url, headers, operation="POST")
    except APIException as ex:
        raise SnipeITAPIException(ex)

    if response.get("status") == "success":
        return True

    messages = response.get("messages", "Unknown error")
    logger.error(f"API returner error response: {messages}")
    return False
