def get_configs(args):
    """Load configuration based on command line arguments."""
    import yaml
    config_file_path = f"configs/{args.environment}/config.yml"

    try:
        with open(config_file_path, "r") as f:
            config = yaml.load(f, Loader=yaml.SafeLoader)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found at path: {config_file_path}.")

    return config