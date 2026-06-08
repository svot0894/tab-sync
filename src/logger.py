from pathlib import Path
from datetime import date, datetime

def configure_logger(base_logs_dir: Path, server: str, environment: str):
    """Configures the logger by creating necessary directories and log file."""
    base_logs_dir.mkdir(parents=True, exist_ok=True)
    log_dir = base_logs_dir / server
    log_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{environment}_update_log_{date.today().strftime('%Y%m%d')}.txt"
    log_file = log_dir / fname
    return log_file

def logger(message: str, log_file: Path) -> None:
    """Logs a message to the specified log file with a timestamp."""
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} - {message}\n")