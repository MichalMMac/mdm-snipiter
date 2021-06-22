#!/opt/local/bin/python3

import logging
import os
import secrets
import sys

from api import jamfpro, snipeit
from api.shared import load_configuration

logging.basicConfig(
    filename="/var/log/mdmsnipiter/jamfsnipiter.log", level=logging.DEBUG
)
logger = logging.getLogger(__name__)


config_path = os.path.join(sys.path[0], "jamf-snipiter.conf")
config_template = [
    {"key": "create_snipeit_users", "default": True},
    {"key": "checkout_rename", "default": True},
    {"key": "category_id"},
    {"key": "manufacturer_id"},
    {"key": "status_id"},
]
config = load_configuration(config_path, config_template)


def get_all_jamf_computers():
    """Fetch all computer records from Jamf"""
    computers = jamfpro.get_all_computers()
    if not computers.get("computers"):
        logging.error("No computers found within JAMF instance")
        sys.exit(0)
    return computers["computers"]


def get_jamf_computer(computer_id):
    """Fetch info about single computer from Jamf"""
    computer = jamfpro.find_computer(computer_id)
    if not computer.get("computer"):
        return None
    return computer["computer"]


def create_snipeit_asset(jamf_asset, snipeit_model_id):
    """Create computer asset within Snipe-IT"""
    payload = {}

    payload["status_id"] = config["status_id"]
    payload["model_id"] = snipeit_model_id
    payload["name"] = jamf_asset["general"]["serial_number"]

    asset_id = snipeit.create_asset(payload)

    payload = {}
    payload["serial"] = jamf_asset["general"]["serial_number"]

    snipeit.patch_asset(asset_id, payload)

    return asset_id


def verify_snipeit_asset(jamf_asset, snipeit_model_id):
    """Ensure asset exists within Snipe-IT and fetch it"""

    serial_number = jamf_asset["general"]["serial_number"]
    if not serial_number:
        return None

    asset = snipeit.find_asset(serial_number)
    if asset is None:
        asset = create_snipeit_asset(jamf_asset, snipeit_model_id)

    return asset


def create_snipeit_model(jamf_computer):
    """Create model within Snipe-IT"""

    payload = {}
    payload["model_number"] = jamf_computer["hardware"]["model_identifier"]
    if jamf_computer["hardware"]["model"]:
        payload["name"] = jamf_computer["hardware"]["model"]
    else:
        payload["name"] = jamf_computer["hardware"]["model_identifier"]
    payload["category_id"] = config["category_id"]
    payload["manufacturer_id"] = config["manufacturer_id"]

    return snipeit.create_model(payload)


def verify_snipeit_model(jamf_computer):
    """Ensure model exists within Snipe-IT and obtain its id"""

    model_identifier = jamf_computer["hardware"]["model_identifier"]
    if not model_identifier:
        return None

    model = snipeit.find_model(model_identifier)
    if model is None:
        model_id = create_snipeit_model(jamf_computer)
    else:
        model_id = model.get("id")

    return model_id


def create_snipeit_user(jamf_computer):
    """Create user within Snipe-IT"""

    payload = {}
    payload["activated"] = False
    payload["username"] = jamf_computer["location"]["username"]

    fullname = jamf_computer["location"]["realname"]
    if fullname:
        tokenized = fullname.split()
        if len(tokenized) > 1:
            payload["last_name"] = " ".join(tokenized[1:])
        payload["first_name"] = tokenized[0]
    else:
        payload["first_name"] = jamf_computer["location"]["username"]

    password = secrets.token_hex(32)
    payload["password"] = password
    payload["password_confirmation"] = password

    if jamf_computer["location"]["email_address"]:
        payload["email"] = jamf_computer["location"]["email_address"]
    if jamf_computer["location"]["phone_number"]:
        payload["phone"] = jamf_computer["location"]["phone_number"]
    if jamf_computer["location"]["position"]:
        payload["jobtitle"] = jamf_computer["location"]["position"]

    return snipeit.create_user(payload)


def verify_snipeit_user(jamf_computer):
    """Ensure user exists within Snipe-IT and fetch id"""

    username = jamf_computer["location"]["username"]

    user = snipeit.find_user(username)
    if user is None and config["create_snipeit_users"]:
        user = create_snipeit_user(jamf_computer)

    return user


def get_asset_checkout_name(jamf_computer, snipeit_user):
    """Determine new asset name which would be used during checkout"""

    if config["checkout_rename"]:
        nicename = snipeit_user["name"]
        nicename += " "
        if jamf_computer["hardware"]["model_identifier"]:
            nicename += jamf_computer["hardware"]["model_identifier"]
        else:
            nicename += "Mac"
        return nicename

    return None


def sync_computers():
    """Syncs computer<->user relationship from Jamf Pro to Snipe-IT"""

    computers = get_all_jamf_computers()

    for item in computers:

        jid = item["id"]
        jamf_computer = get_jamf_computer(jid)
        if jamf_computer is None:
            logging.error(
                "Jamf computer record not found even though it should be there"
            )
            continue

        snipeit_model_id = verify_snipeit_model(jamf_computer)
        if snipeit_model_id is None:
            logging.error(f"Unable to obtain Snipe-IT model identifier ({jid})")
            continue

        logging.debug(f"Found Snipe-IT model id: {snipeit_model_id} ({jid})")

        snipeit_computer_asset = verify_snipeit_asset(jamf_computer, snipeit_model_id)
        if snipeit_computer_asset is None:
            logging.error(f"Unable to obtain Snipe-IT computer identifier ({jid})")
            continue

        logging.debug(
            f"Found Snipe-IT asset id: {snipeit_computer_asset['id']} ({jid})"
        )

        username = jamf_computer["location"]["username"]
        if not username:
            logging.info(
                f"Jamf Pro computer record does not have user assigned ({jid})"
            )
            continue

        snipeit_user = verify_snipeit_user(jamf_computer)
        if snipeit_user is None:
            logging.error(f"Unable to get Snipe-IT user id ({jid})")
            continue

        asid = snipeit_computer_asset["id"]
        nicename = get_asset_checkout_name(jamf_computer, snipeit_user)

        if snipeit_computer_asset["assigned_to"] is None:
            logging.info(f"Checking out to user {username} ({jid})")
            snipeit.checkout(asid, snipeit_user["id"], nicename)
        elif snipeit_computer_asset["assigned_to"]["username"] == username:
            logging.debug(
                f"Snipe-IT asset {asid} already has an user {username} assigned ({jid})"
            )
            continue
        else:
            logging.info(
                f"Changing assigned user withing Snipe-IT to {username} ({jid})"
            )
            snipeit.checkin(asid)
            snipeit.checkout(asid, snipeit_user["id"], nicename)


def main():
    """Main"""
    sync_computers()


if __name__ == "__main__":
    main()
