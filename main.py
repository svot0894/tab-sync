from src.cli import get_args
from src.configs import get_configs
from src.runner import run


def main() -> None:
    try:
        # parse command line arguments and load configurations
        args = get_args()
        config = get_configs(args)

        # execute main process
        run(config, args)
    except Exception as e:
        print(f"Critical error in main execution: {str(e)}.")

if __name__ == "__main__":
    main()