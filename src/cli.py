import argparse

def get_args():
    """Parse command line arguments."""
    p = argparse.ArgumentParser(
    description="Required arguments to run updates."
    )
    p.add_argument(
        "-r",
        "--rotate",
        action="store_true",
        help="If set, the tool will rotate the passwords/tokens for the database connections."
    )
    p.add_argument(
        "-e",
        "--environment",
        type=str,
        choices=["dev", "test", "uat", "prod"],
        help="Tells the tool which environment to update."
    )
    p.add_argument(
        "-s",
        "--server",
        type=str,
        choices=["server1", "server2"],
        help="Tells the tool which Tableau Server to update."
    )
    p.add_argument(
        "-d",
        "--dry_run",
        action="store_true",
        help="If set, the tool will not make any changes to the Tableau Server."
    )
    return p.parse_args()