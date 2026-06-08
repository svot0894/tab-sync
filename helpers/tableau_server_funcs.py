# Helper functions for interacting with Tableau Server REST API.

import requests
import xml.etree.ElementTree as ET

# TEMP: disable 'InsecureRequestWarning'
requests.packages.urllib3.disable_warnings()  # type: ignore

def sign_in(url: str, pat_name: str, pat_secret: str, site: str) -> tuple:
    """
    Signs in to the Tableau Server using a personal access token.

    'url'         base server URL
    'pat_name'    personal access token name
    'pat_secret'  personal access token secret
    'site'        site content URL

    Returns the authentication token and site ID.
    """
    url = f"{url}/auth/signin"
    xmlns = {'t': 'http://tableau.com/api'}

    # Build the request XML
    xml_request = ET.Element('tsRequest')
    credentials_element = ET.SubElement(
        xml_request,
        'credentials',
        personalAccessTokenName=pat_name,
        personalAccessTokenSecret=pat_secret
    )
    ET.SubElement(credentials_element, 'site', contentUrl=site)
    xml_request = ET.tostring(xml_request)

    # Make the request to server
    server_response = requests.post(url, data=xml_request, verify=False)
    server_response.raise_for_status()

    # Parse the response
    parsed_response = ET.fromstring(server_response.text)

    # Get the auth token and site ID
    token = parsed_response.find('t:credentials', namespaces=xmlns).get('token')
    site_id = parsed_response.find('.//t:site', namespaces=xmlns).get('id')
    return token, site_id

def sign_out(url: str, auth_token: str) -> None:
    """
    Destroys the active session and deletes authentication token.

    'url'           base server URL
    'auth_token'    authentication token that grants user access to API calls
    """
    url = f"{url}/auth/signout"

    server_response = requests.post(url, headers={'x-tableau-auth': auth_token}, verify=False)
    server_response.raise_for_status()

    return

def get_objects(url: str, site_id: str, headers: dict, object_type: str) -> list:
    """
    Fetches all objects of a given type (datasources, flows, workbooks).

    'url'          base server URL
    'site_id'      site ID
    'headers'      request headers including auth token
    'object_type'  type of object to fetch (e.g., "datasources", "flows", "workbooks")

    Returns a list of objects.
    """
    url = f"{url}/sites/{site_id}/{object_type}"
    xmlns = {'t': 'http://tableau.com/api'}
    params = {'pageSize': 1000}

    resp = requests.get(url, params=params, headers=headers, verify=False)
    resp.raise_for_status()

    xml_response = ET.fromstring(resp.text)
    objects = xml_response.findall(f".//t:{object_type[:-1]}", namespaces=xmlns)

    return objects

def get_connections(url: str, site_id: str, headers: dict, object_type: str, object_id: str) -> list:
    """
    Fetches all connections for a given object.

    'url'          base server URL
    'site_id'      site ID
    'headers'      request headers including auth token
    'object_type'  type of object (e.g., "datasources", "flows", "workbooks")
    'object_id'    ID of the specific object

    Returns a list of connections.
    """
    url = f"{url}/sites/{site_id}/{object_type}/{object_id}/connections"
    xmlns = {'t': 'http://tableau.com/api'}

    resp = requests.get(url, headers=headers, verify=False)
    resp.raise_for_status()

    xml_response = ET.fromstring(resp.text)
    connections = xml_response.findall(f".//t:connection", namespaces=xmlns)

    return connections

def update_connection(url: str, site_id: str, headers: dict, object_type: str, object_id: str, connection_id: str, payload: dict) -> requests.Response:
    """
    Updates a specific connection for a given object.

    'url'           base server URL
    'site_id'       site ID
    'headers'       request headers including auth token
    'object_type'   type of object (e.g., "datasources", "flows", "workbooks")
    'object_id'     ID of the specific object
    'connection_id' ID of the specific connection to update
    'payload'       dict with connection update details

    Returns the server response.
    """
    url = f"{url}/sites/{site_id}/{object_type}/{object_id}/connections/{connection_id}"
    resp = requests.put(url, headers=headers, json=payload, verify=False)
    resp.raise_for_status()

    return resp