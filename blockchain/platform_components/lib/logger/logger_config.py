import sys
from datetime import datetime
import logging
import os


def configure_logging(file_type="app"):
    # Suppress loggers of certain libraries
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger('tensorflow').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)

    debugger_enabled = os.getenv("DEBUGGER_ENABLED", "False").lower() == "true"

    # Create handlers
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_directory = f"./../../logs/{current_time}"
    os.makedirs(log_directory, exist_ok=True) # dynamically created

    # Configure console level based on debugger setting
    console_level = logging.DEBUG if debugger_enabled else logging.INFO

    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(f"{log_directory}/{file_type}.log"),
            logging.StreamHandler()
        ]
    )

    # Adjust console handler level separately (since basicConfig doesn't let us set different levels)
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            handler.setLevel(console_level)
