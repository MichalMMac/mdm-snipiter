"""
Jamf Pro API module

Module to communicate with defined Jamf Pro instance.
Requires jamfpro.conf JSON file within the same directory.
"""

import base64
import json
import logging
import os
import sys

from .shared import APIException, contact_api

logger = logging.getLogger(__name__)


class JamfProAPIException(Exception):
    """Expection for the Jamf Pro API module"""


# Configure Jamf Pro API module
try:
    with open(os.path.join(sys.path[0], "api", "jamfpro.conf")) as jfile:
        config = json.load(jfile)

        jamfpro_url = config.get("url")
        if not jamfpro_url:
            raise JamfProAPIException("Configuration file is missing 'url'")

        username = config.get("username")
        if not username:
            raise JamfProAPIException("Configuration file is missing 'username'")

        password = config.get("password")
        if not password:
            raise JamfProAPIException("Configuration file is missing 'password'")

        attempts = config.get("attempts", 5)

except JamfProAPIException:
    raise
except FileNotFoundError:
    raise JamfProAPIException("Configuration file 'jamfpro.conf' is missing")
except Exception:
    raise JamfProAPIException("Error reading 'jamfpro.conf' configuration file")


classic_api_endpoint = f"{jamfpro_url}/JSSResource"
base64_auth = base64.b64encode(f"{username}:{password}".encode()).decode()
classic_headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Basic {base64_auth}",
}

# Code for Jamf moder API access
#
# api_endpoint = f"{jamfpro_url}/uapi"
# logger.debug("Getting JAMF API token")
# try:
#     data = contact_api(f"{api_endpoint}/auth/tokens", classic_headers, type="POST")
# except APIException as ex:
#     raise JamfProAPIException(ex)
#
# token = data.get("token")
# if not token:
#     raise JamfProAPIException("Unable to obtain API authenticaion token")
#
# headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}


def get_data_from_classic_api(url):
    """Get generic data object from Jamf Classic API"""
    try:
        data = contact_api(url, classic_headers, notfound404=True)
    except APIException as ex:
        raise JamfProAPIException(ex)

    return data


def find_computer(computer_id):
    """Find single computer object by its id"""
    return get_data_from_classic_api(
        f"{classic_api_endpoint}/computers/id/{computer_id}"
    )


def get_all_computers():
    """Find all computer objects"""
    return get_data_from_classic_api(f"{classic_api_endpoint}/computers")


def find_user(user_id):
    """Find single user object by its id"""
    return get_data_from_classic_api(f"{classic_api_endpoint}/users/id/{user_id}")


def find_user_by_name(user_name):
    """Find single user object by its name"""
    return get_data_from_classic_api(f"{classic_api_endpoint}/users/name/{user_name}")
