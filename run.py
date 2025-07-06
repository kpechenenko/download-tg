import argparse
import asyncio
import logging
import os
import sys

import app
import config
import repository


def setup_logging(log_file: str, log_level: int = logging.INFO) -> logging.Logger:
    """
    Configures logging to output to both the console and a specified log file.

    :param log_file: Path to the log file where logs will be written.
    :param log_level: Logging level (e.g., logging.INFO).
    :return: Logger instance configured with console and file handlers.
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


async def main() -> None:
    """
    Main function to parse arguments, set up services, and run the download application.
    :return:
    """
    parser = argparse.ArgumentParser(
        description="Download files from a Telegram channel based on a config file."
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
        log.info(f"Videos download directory set to: '{cfg.storage.video_dir}'")

        os.makedirs(cfg.storage.audio_dir, exist_ok=True)
        log.info(f"Audios download directory set to: '{cfg.storage.audio_dir}'")

        repo = repository.SqliteFileDownloadHistoryRepository(cfg.storage.sqlite_file)
        log.info("Initialized database repository.")

        downloader = app.DownloadFilesApp(repo, cfg, log)
        await downloader.download_and_save()
    except Exception:
        log.exception(f"critical error occurred in the application")
    finally:
        if repo and hasattr(repo, 'close_conn'):
            await repo.close_conn()


if __name__ == "__main__":
    asyncio.run(main())
