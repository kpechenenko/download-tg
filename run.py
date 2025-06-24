import argparse
import asyncio
import logging
import os
import sys

import config
import repository
import app


def setup_logging(log_file: str, log_level: int = logging.INFO) -> logging.Logger:
    """
    Configures logging to output to both the console and a specified log file.
    """
    log = logging.getLogger()
    log.setLevel(log_level)

    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    log.addHandler(console_handler)

    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(log_formatter)
            log.addHandler(file_handler)
        except Exception as e:
            log.error(f"Failed to create file handler for logging at {log_file}: {e}")

    return log


async def main():
    """
    Main function to parse arguments, set up services, and run the download application.
    """
    parser = argparse.ArgumentParser(
        description="Download videos from a Telegram channel based on a config file."
    )
    parser.add_argument(
        "config_path",
        help="Path to the YAML configuration file."
    )
    args = parser.parse_args()

    try:
        cfg = config.Config.load_from_yaml(args.config_path)
    except FileNotFoundError:
        print(f"Error: Configuration file not found at '{args.config_path}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading or parsing config file '{args.config_path}': {e}", file=sys.stderr)
        sys.exit(1)

    log = setup_logging(cfg.app.log_file)

    repo = None
    try:
        os.makedirs(cfg.storage.video_dir, exist_ok=True)
        log.info(f"Video download directory set to: '{cfg.storage.video_dir}'")

        repo = repository.SqliteVideoDownloadHistoryRepository(cfg.storage.sqlite_file)
        log.info("Initialized database repository.")

        downloader = app.DownloadVideoApp(repo, cfg, log)
        await downloader.download_and_save()
    except Exception:
        log.exception(f"critical error occurred in the application")
    finally:
        if repo and hasattr(repo, 'close_conn'):
            await repo.close_conn()


if __name__ == "__main__":
    asyncio.run(main())
