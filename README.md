# MDM Snipiter

A set of tools for state synchronisation between MDM systems and [Snipe-IT](https://snipe-it.readme.io/docs)
inventory management. Tools mostly leverage various APIs and webhook mechanisms.

Requirements:

- Python 3.8 or newer
- Python [Requests](https://docs.python-requests.org/en/master/) library
- Snipe-IT muse have the `Generate auto-incrementing asset IDs` option **enabled**


## jamf-snipiter

`jamf-snipiter.py` synchronises the computer<->user relations ship from Jamf Pro to
Snipe-IT.

It works in following fashion:

1. Get list of all computer object from Jamf Pro.
2. Iterate over the list of all computers.
3. Verify & Create
   - Verify if corresponding model exist in Snipe-IT. Create if necessary.
   - Verify if corresponding asset exist in Snipe-IT. Create if necessary.
   - Verify if the computer is assigned to the user in Jamf Pro.
     In not, continue to the next computer.
   - Verify if corresponding user exist in Snipe-IT. Create if `create_snipeit_users`
     option is set to `true` (default: yes).
7. Checkout
  - If `checkout_rename` option is set to `true` (default: yes), prepare a new name
    to be used for the asset if checkout out.
  - If Snipe-IT asset is not assigned to a user, do the checkout.
  - If Snipe-IT asset is already checked out to the user, continue to the next computer.
  - If Snipe-IT asset is already checked out to a different user, initiate a checkin
    following with the checkout to correct user

Important notes:

- We are using Jamf Pro [Classic API](https://www.jamf.com/developers/apis/classic/)
to access Jamf Pro instance resources. Newer API is not yer up to the task.
- Jamf Pro API is currently used only for GET operations. We don't sync anything from
  Snipe-IT.
- Synchronisation of object contents from Jamf Pro to Snipe-IT only happens when
  `jamf-snipiter.py` creates new object in Snipe-IT. If any values differ between
  corresponding Jamf Pro object and Snipe-IT object, they are not synchronised. Exception
  to this behavior is the relationship between compter and the user. `jamf-snipiter.py`
  will always try to (`checkin` and) `checkout` the assents to the users according to
  relationship within the Jamf Pro.

### Configuration

Configure `jamf-snipiter.py`:

1. Create configuration file: `cp jamf-snipiter.conf.sample jamf-snipiter.conf`
2. Provide required variables.
3. Ensure `log_path` directory is writable by the user executing the `jamf-snipiter.py`

Variable name        | Required | Default Value | Description
-------------------- | -------- | ------------- | -----------
checkout_rename      | no       | true          | Create a nice name for computers being checked out. Format is: `Full Name ModelIdentifier` (John Appleseed Macmini8,1).
create_snipeit_users | no       | true          | Create Snipe-IT user object when they are not found by the username from Jamf computer object.
log_path             | no       | `/var/log/mdmsnipiter/jamfsnipiter.log` | Log file path.
log_level            | no       | WARN          | Logging [level](https://docs.python.org/3/library/logging.html#logging-levels).
category_id          | yes      |               | ID of Snipe-IT category object to be used when creating new Snipe-IT **model** objects.
manufacturer_id      | yes      |               | ID of Snipe-IT manufacturer object to be used when creating new Snipe-IT **model** objects.
status_id            | yes      |               | ID of Snipe-IT manufacturer status to be used when creating new Snipe-IT **asset** objects.

Configure Snipe-IT API access:

1. Create configuration file: `cp api/snipeit.conf.sample api/snipeit.conf`
2. Provide required variables.
3. Make sure configuration is readable only by desired users/groups.

Variable name | Required | Default Value | Description
------------- | -------- | ------------- | -----------
attempts      | no       | 3             | Number of attempts when trying to get a valid response from API. After `attempts` failures `jamf-snipiter.py` terminates with an exception.
token         | yes      |               | Snipe-IT API token.
url           | yes      |               | URL of Snipe-IT instance.

Configure Jamf Pro API access:

1. Create configuration file: `cp api/jamfpro.conf.sample api/jamfpro.conf`
2. Provide required variables.
3. Make sure configuration is readable only by desired users/groups.

Variable name | Required | Default Value | Description
------------- | -------- | ------------- | -----------
attempts      | no       | 3             | Number of attempts when trying to get a valid response from API. After `attempts` failures `jamf-snipiter.py` terminates with an exception.
username      | yes      |               | Username of a Jamf Pro user with API access privileges.
pasword       | yes      |               | Password for that user.
url           | yes      |               | URL of Jamf Pro instance.


### Object synchronisation

When necessary object is missing in the Snipe-IT, `jamf-snipiter.py` attempts to create it.
Attributes are copied in the following manner.

Snipe-IT model object:

| Snipe-IT atributes <- | <- Jamf Pro attributes
| --------------------- | ----------------------------------------
| model['model_number'] | computer["hardware"]["model_identifier"]
| model['name']         | First choice: computer["hardware"]["model"], Second choice: computer["hardware"]["model_identifier"]
| category_id           | Configured in `jamf-snipiter.conf``
| manufacturer_id       | Configured in `jamf-snipiter.conf``

Snipe-IT Asset object:

| Snipe-IT atributes <- | <- Jamf Pro attributes
| --------------------- | ----------------------------------------
| hardware['status_id'] | Configured in `jamf-snipiter.conf``
| hardware['model_id']  | Id of corresponding model object
| hardware["serial"]    | Configured in `jamf-snipiter.conf``
| manufacturer_id       | computer["general"]["serial_number"]

Snipe-IT User object:

| Snipe-IT atributes <- | <- Jamf Pro attributes
| --------------------- | ----------------------------------------
| user['activated']     | false
| user['username']      | computer["location"]["username"]
| payload["first_name"] | First part of the name (delimited by space) in computer["location"]["realname"]
| payload["last_name"]  | Rest of the names after the first space delimiter (if any).
| payload["password"]   | Random string
| payload["email"]      | computer["location"]["email_address"]
| payload["phone"]      | computer["location"]["phone_number"]
| payload["jobtitle"]   | computer["location"]["position"]


### Limitations

- Asset tags are not synchronised between Jamf Pro and Snipe-IT
- iOS devices are not synchronised from Jamf Pro to Snipe-IT
- All new model objects are created with the one predefined category.
- Additional computer information could synchronized:
    - order_number -> po_number
    - warranty_months -> warranty_expires
    - purchase_cost -> purchase_price
    - purchase_date -> po_date
- Additional user information could synchronized:
    - departnemt
