from ruamel.yaml import YAML    # type: ignore
import requests
from datetime import date, datetime
import csv
import os
import re

import snowflake.connector as sc    # type: ignore


########     helper functions     ########


def update_cfg_file(server: str, site_name: str, db_key: str, new_pwd: str) -> None:
    """Update the configuration YAML file with the new password."""
    try:
        site = re.sub(r'\d+', '', site_name)

        yaml = YAML(typ='rt')
        yaml.indent(mapping=2, sequence=4, offset=2)  # Match original indentation

        config_path = f"configs/{site}/config.yml"
        with open(config_path, "r") as f:
            config = yaml.load(f)

        # Update password in config
        config["tableau_servers"][server]["database_connections"][db_key]["db_password"] = new_pwd

        with open(config_path, "w") as f:
            yaml.dump(config, f)

    except Exception as e:
        raise Exception(f"Error updating config file: {str(e)}.")

  
def save_new_pwd(server: str, site_name: str, db_key: str, db_username: str, new_pwd: str) -> None:
    """
    Stores generated password in a CSV file.
    """
    try:
        file_path = f"exports/new_pwds_{date.today().isoformat()}.csv"
        
        # Ensure exports directory exists
        os.makedirs("exports", exist_ok=True)

        # read existing data if file exists
        rows = []
        header = ["server", "site_name", "db_key", "db_username", "new_pwd", "creation_datetime"]
        file_exists = os.path.exists(file_path)

        if file_exists:
            with open(file_path, "r", newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
                if rows and rows[0] == header:
                    header = rows.pop(0)    # keep header, remove from data
                
        # check if same entry already exists in the file
        found = False
        for i, row in enumerate(rows):
            if (
                len(row) >= 4
                and row[0] == server
                and row[1] == site_name
                and row[2] == db_key
                and row[3] == db_username
            ):
                # update existing row
                rows[i] = [
                    server,
                    site_name,
                    db_key,
                    db_username,
                    new_pwd,
                    datetime.now().isoformat()
                ]
                found = True
                break
        
        # if not found, append new row
        if not found:
            rows.append([
                    server,
                    site_name,
                    db_key,
                    db_username,
                    new_pwd,
                    datetime.now().isoformat()
                ])
        
        # write data back to file
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        
    except Exception as e:
        raise Exception(f"Error saving new password: {str(e)}.")


def rotate_pwd(server: str, site: str, db_key: str, db: dict) -> str:
    """Determine which password rotation function to call based on db_key."""
    func_name = f"rotate_{db_key.lower()}_pwd"

    if func_name in globals():
        return globals()[func_name](server, site, db)
    else:
        raise ValueError(f"No '{func_name}' function was found.")


########     Password rotation functions for specific databases     ########


def rotate_snowflake_pwd(server: str, site: str, db: dict) -> str:
    """
    Rotate Snowflake Programmatic Access Token (PAT) using SSO authentication.

    Requires SYSADMIN to be granted the "CREATE TOKEN" privilege on the user.
    GRANT MODIFY PROGRAMMATIC AUTHENTICATION METHODS ON USER my_service_user TO ROLE my_service_owner_role;
    
    """
    try:
        # Extract access credentials
        db_access_username = db.get("db_access_username")
        db_account = db.get("db_account")

        # Extract username for PAT naming
        db_username = db.get("db_username")         # user being rotated
        pat_name = db.get("db_pat_name")

        if not all([db_access_username, db_account, db_username, pat_name]):
            raise ValueError("Missing required Snowflake credentials: db_username, db_account, db_access_username, or pat_name.")

        # Connect to Snowflake via SSO
        conn = sc.connect(
            user=db_access_username,
            account=db_account,
            authenticator="externalbrowser",
        )
        cursor = conn.cursor()
        alter_cmd = f'ALTER USER {db_username} ROTATE PROGRAMMATIC ACCESS TOKEN {pat_name}'

        # Fetch the new token
        _, new_token, _ = cursor.execute(alter_cmd).fetchone()

        if not new_token:
            raise Exception("New programmatic access token is empty or not returned.")

        # Save and update config
        save_new_pwd(server=server, site_name=site, db_key="snowflake", db_username=db_username, new_pwd=new_token)
        update_cfg_file(server=server, site_name=site, db_key="snowflake", new_pwd=new_token)

        return new_token

    except Exception as e:
        raise Exception(f"Error rotating Snowflake password (PAT): {str(e)}")


def get_azure_sp_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Get Azure Service Principal token."""

    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    scope = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d/.default"

    payload = {
        "client_id": client_id,
        "scope": scope,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        raise Exception(f"Error getting Azure SP token: {str(e)}.")


def rotate_databricks_pwd(server: str, site: str, db: dict) -> str:
    """Rotate Databricks PAT using Azure SP token."""

    # prepare Azure credentials
    tenant_id = db.get("tenant_id")
    client_id = db.get("client_id")
    client_secret = db.get("client_secret")
    
    if not tenant_id or not client_id or not client_secret:
        raise ValueError("Missing required Azure credentials: tenant_id, client_id, or client_secret.")
    
    azure_token = get_azure_sp_token(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret
    )
    if not azure_token:
        raise Exception("Failed to get Azure SP token.")

    # use Azure token to call Databricks API
    url = f"{db.get('workspace_url')}/api/2.0/token/create"
    headers = {
        "Authorization": f"Bearer {azure_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "comment": "Rotated by automation.",
        "lifetime_seconds": 15778800  # 6 months
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        new_pwd = result.get("token_value")
        if not new_pwd:
            raise ValueError("No 'token_value' in response.")

        # save new password
        save_new_pwd(server=server, site_name=site, db_key="databricks", db_username="", new_pwd=new_pwd)
        update_cfg_file(server=server, site_name=site, db_key="databricks", new_pwd=new_pwd)

        return new_pwd
    except Exception as e:
        raise Exception(f"Error rotating Databricks password: {str(e)}.")