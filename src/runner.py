from pathlib import Path
from datetime import datetime
from .logger import (
    configure_logger,
    logger
)
from helpers.pwd_rotation_funcs import (
    rotate_pwd,
)
from helpers.tableau_server_funcs import (
    sign_in,
    sign_out,
    get_objects,
    get_connections,
    update_connection
)

def run(config, args):
    """Run the main update process based on the provided configuration and arguments."""
    # prepare logging file
    log_file_name = configure_logger(Path(config.get("base_logs_dir")), args.server, args.environment)

    # extract server and database configurations
    server_confs = config.get("tableau_servers", {}).get(args.server, {}).get("tableau_server_info", {})
    if not server_confs:
        raise ValueError(f"Server configuration not found for '{args.server}'.")

    db_confs = config.get("tableau_servers", {}).get(args.server, {}).get("database_connections", {})
    if not db_confs:
        raise ValueError(f"No database connections configured for '{args.server}'.")

    # prepare base URL and authentication details
    url = f"{server_confs.get('tableau_server', '')}/api/{server_confs.get('api_version', '')}"
    pat_name = server_confs.get("token_name")
    pat_secret = server_confs.get("token_secret")

    if not pat_name or not pat_secret:
        raise ValueError("Token name or secret is missing in the server configuration.")

    for site in server_confs.get("sites", []).split(","):
        try:
            logger(f"{'[DRY-RUN] ' if args.dry_run else ''}Starting updates for '{site}' site on Tableau '{args.server}' server...", log_file_name)

            # sign in to Tableau Server via REST API and get auth token
            auth_token, site_id = sign_in(
                url = url,
                pat_name = pat_name,
                pat_secret = pat_secret,
                site = site
            )

            # set up request headers
            headers = {
                "X-Tableau-Auth": auth_token,
                "Content-Type": "application/json"
            }

            for db_key, db in db_confs.items():
                try:
                    logger(f"{'[DRY-RUN] ' if args.dry_run else ''}Starting update of {db_key}-type connections...", log_file_name)

                    # get required db connection details
                    db_server_name = db.get("db_server_name")
                    db_username = db.get("db_username")

                    if not db_server_name:
                        raise ValueError(f"Database server name or username missing for '{db_key}' connection.")

                    # TBD: fetch password/token from config or rotation function
                    if args.rotate:
                        db_password = rotate_pwd(args.server, site, db_key, db)
                    else:
                        db_password = db.get("db_password")
                    
                    if not db_password:
                        raise ValueError(f"Database password missing for '{db_key}' connection.")

                    # iterate through each object type to update connections
                    for obj_type in config["objects"]:
                        try:
                            if obj_type not in ["datasources", "flows", "workbooks"]:
                                logger(f"Skipping unknown object type: {obj_type}", log_file_name)
                                continue

                            logger(f"{'[DRY-RUN] ' if args.dry_run else ''}Processing object type: {obj_type}...", log_file_name)
                            all_objects = get_objects(url, site_id, headers, obj_type)

                            for obj in all_objects:
                                obj_id = obj.get("id")
                                obj_name = obj.get("name")

                                try:
                                    connections = get_connections(url, site_id, headers, obj_type, obj_id)
                                except Exception as e:
                                    raise Exception(f"{obj_name} - ERROR fetching connections: {e}.")
                                
                                for conn in connections:
                                    if conn.get("serverAddress") == db_server_name and conn.get("userName") == db_username:
                                        
                                        payload = {
                                            "connection": {
                                                "serverAddress": db_server_name,
                                                "userName": db_username,
                                                "password": db_password,
                                                "embedPassword": "true"
                                            }
                                        }
                                        
                                        if args.dry_run:
                                            logger(f"{obj_name} - ConnID: {conn.get('id')} - Status: DRY-RUN - Time: {datetime.now().isoformat()}", log_file_name)
                                            continue
                                        resp = update_connection(
                                            url,
                                            site_id,
                                            headers,
                                            obj_type,
                                            obj_id,
                                            conn.get("id"),
                                            payload
                                        )

                                        status = "OK" if resp.status_code == 200 else f"NOK - ({resp.text})"
                                        logger(f"{obj_name} - ConnID: {conn.get('id')} - Status: {status} - Time: {datetime.now().isoformat()}", log_file_name)
                        except Exception as e:
                            raise Exception(f"Error processing object type '{obj_type}': {str(e)}.")
                    logger(f"{'[DRY-RUN] ' if args.dry_run else ''}Completed update for {db_key}-based connections.", log_file_name)
                except Exception as e:
                    raise Exception(f"Error updating {db_key}-type connections: {str(e)}.")

            # sign out to close the session
            sign_out(
                url = url,
                auth_token = auth_token
            )
            logger(f"{'[DRY-RUN] ' if args.dry_run else ''}Completed updates for '{site}' site on Tableau '{args.server}' server...", log_file_name)
        except Exception as e:
            raise Exception(f"Error processing site '{site}': {str(e)}.")