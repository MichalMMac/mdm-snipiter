"""
Snipe-IT API module

Module to communicate with defined Snipe-IT instance.
Requires snipeit.conf JSON file within the same directory.
"""
import logging
import os
import sys

from .shared import APIException, contact_api, load_configuration

logger = logging.getLogger(__name__)


class SnipeITAPIException(Exception):
    """Expection for the Snipe-IT API module"""


config_path = os.path.join(sys.path[0], "api", "snipeit.conf")
config_template = [{"key": "attempts", "default": 3}, {"key": "token"}, {"key": "url"}]
config = load_configuration(config_path, config_template)

api_endpoint = f"{config['url']}/api/v1"
headers = {"Accept": "application/json", "Authorization": f"Bearer {config['token']}"}


def get_data_from_api(url):
    """Return rows of date from API"""
    try:
        data = contact_api(url, headers, attempts=config["attempts"])
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

    logger.debug("No item found")
    return None


def find_asset(serial):
    """Try to find Snipe-IT asset by its serial number"""

    logger.debug(f"Searching for asset with serial number: {serial}")
    return get_single_item_from_api(f"{api_endpoint}/hardware/byserial/{serial}")


def find_model(identifier):
    """Try to find Snipe-IT model by its identifier"""

    logger.debug(f"Searching for model with identifier: {identifier}")
    return get_single_item_from_api(f"{api_endpoint}/models?search={identifier}")


def find_user(username):
    """Try to find Snipe-IT user by its username"""

    logger.debug(f"Searching for user with username: {username}")
    return get_single_item_from_api(f"{api_endpoint}/users?search={username}")


def modify_item(url, payload, operation, item_name):
    """Use API to create or modify target item"""
    try:
        response = contact_api(
            url,
            headers,
            payload=payload,
            operation=operation,
            attempts=config["attempts"],
        )
    except APIException as ex:
        raise SnipeITAPIException(ex)

    if response.get("status") == "success":
        return response["payload"]

    messages = response.get("messages", "Unknown error")
    logger.error(f"API returned error response: {messages}")
    raise SnipeITAPIException(f"Unable to create item {item_name}")


def create_item(url, payload, item_name):
    """POST wrapper function for modify_item"""
    return modify_item(url, payload, "POST", item_name)


def patch_item(url, payload, item_name):
    """PATCH wrapper function for modify_item"""
    return modify_item(url, payload, "PATCH", item_name)


def create_asset(payload):
    """Create new asset"""
    asset_name = payload["name"]
    logger.info(f"Creating new asset {asset_name}")
    return create_item(f"{api_endpoint}/hardware", payload, asset_name)


def patch_asset(asset_id, payload):
    """Patch existing new asset"""
    logger.info(f"Patching asset {asset_id}")
    return patch_item(f"{api_endpoint}/hardware/{asset_id}", payload, asset_id)


def create_model(payload):
    """Create new model"""
    model_name = payload["name"]
    logger.info(f"Creating new model {model_name}")
    return create_item(f"{api_endpoint}/models", payload, model_name)


def create_user(payload):
    """Create new user"""
    user_name = payload["username"]

    logger.info(f"Creating new user {payload['username']}")
    return create_item(f"{api_endpoint}/users", payload, user_name)


def checkout(asset_id, user_id, asset_name=None):
    """Assign user to the asset"""

    logger.info(f"Checking out asset: {asset_id} to user: {user_id}")

    url = f"{api_endpoint}/hardware/{asset_id}/checkout"
    payload = {"checkout_to_type": "user", "assigned_user": user_id}
    if asset_name:
        payload["name"] = asset_name

    try:
        response = contact_api(
            url, headers, payload=payload, operation="POST", attempts=config["attempts"]
        )
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
        response = contact_api(
            url, headers, operation="POST", attempts=config["attempts"]
        )
    except APIException as ex:
        raise SnipeITAPIException(ex)

    if response.get("status") == "success":
        return True

    messages = response.get("messages", "Unknown error")
    logger.error(f"API returner error response: {messages}")
    return False
