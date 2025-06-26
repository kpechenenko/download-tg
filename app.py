import asyncio
import datetime
import logging
import os
import uuid
from typing import List, Coroutine, Any

from telethon import TelegramClient
from telethon.tl import custom, types

import config
import repository


class DownloadVideoApp:
    """
    Service to download video from TG restricted channels.
    """
    def __init__(self, repo: repository.SqliteVideoDownloadHistoryRepository, cfg: config.Config, log: logging.Logger):
        self._repo = repo
        self._cfg = cfg
        self._log = log
        self._client = TelegramClient(
            self._cfg.user.session_file,
            self._cfg.user.api_id,
            self._cfg.user.api_hash
        )

    def _make_video_id(self, msg: custom.message.Message) -> str:
        """
        Creates a unique identifier for a video based on channel, message, and video IDs.

        :param msg: The Telegram message object containing the video.
        :return: A string representing the unique video identifier in the format 'channel_id.message_id.video_id'.
        """
        return f"{self._cfg.search.channel_id}.{msg.id}.{getattr(msg.video, 'id', 'unknown')}"

    def _message_contains_all_keywords(self, msg: custom.message.Message) -> bool:
        """
        Checks if the message text contains all specified keywords.

        :param msg: The Telegram message to check for keywords.
        :return: True if all specified keywords are present in the message text, False otherwise.
        """
        if not self._cfg.search.key_words:
            return True
        if not msg.text:
            return False
        words_in_message = set(msg.text.lower().split())
        required_keywords = {w.lower() for w in self._cfg.search.key_words}
        return required_keywords.issubset(words_in_message)

    async def _download_and_process_video(
            self,
            message: custom.message.Message,
            channel: types.Channel,
            semaphore: asyncio.Semaphore
    ) -> bool:
        """
        Acquires the semaphore, downloads a single video from the provided message, writes metadata to the repository, and releases the semaphore.

        :param message: The Telegram message containing the video to download.
        :param channel: The Telegram channel object from which the message was retrieved.
        :param semaphore: An asyncio.Semaphore to limit concurrent downloads.
        :return: True if the video was downloaded and processed successfully, False otherwise.
        """
        video_id = self._make_video_id(message)
        out_file = os.path.join(self._cfg.storage.video_dir, f"{video_id}.mp4")

        async with semaphore:
            try:
                self._log.info(f"Starting download for video {video_id} from message {message.id}")

                await self._client.download_media(message.media, out_file)

                self._log.info(f"Finished downloading video {out_file}. Writing to repository...")

                video_record = repository.DownloadedVideo(
                    id=str(uuid.uuid4()),
                    channel_id=channel.id,
                    message_id=str(message.id),
                    text=message.text or "",
                    filename=os.path.abspath(out_file),
                    created=datetime.datetime.now(datetime.timezone.utc),
                )
                await self._repo.write(video_record)
                self._log.info(f"Successfully saved metadata for video {out_file}")
                return True

            except Exception as e:
                self._log.exception(f"Failed to download or process video {video_id} from message {message.id}: {e}")
                if os.path.exists(out_file):
                    try:
                        os.remove(out_file)
                    except OSError as ose:
                        self._log.error(f"Error removing partially downloaded file {out_file}: {ose}")
                return False

    async def download_and_save(self) -> None:
        """
        Initiates the video download process by connecting to Telegram, scanning messages in the specified channel, and downloading new videos concurrently.

        :return:
        """
        self._log.info("Starting video download process...")

        try:
            await self._repo.open_conn()
            existing_ids = await self._repo.get_video_ids(self._cfg.search.channel_id)
            self._log.info(f"Found {len(existing_ids)} existing video records for this channel.")
        except Exception as e:
            self._log.exception(f"Fatal: Could not get existing video IDs from repository. Aborting. Error: {e}")
            return

        semaphore = asyncio.Semaphore(self._cfg.app.download_at_same_time_size)
        tasks: List[Coroutine[Any, Any, bool]] = []

        async with self._client:
            self._log.info("Telegram client started and connected.")

            try:
                self._log.info(f"Connecting to channel: '{self._cfg.search.channel_id}'")
                channel = await self._client.get_entity(self._cfg.search.channel_id)
                self._log.info(f"Successfully connected to channel '{getattr(channel, 'title', 'N/A')}'")
            except Exception as e:
                self._log.exception(f"Fatal: Could not connect to channel '{self._cfg.search.channel_id}'. Aborting. Error: {e}")
                return

            self._log.info("Scanning for new videos...")
            try:
                async for message in self._client.iter_messages(channel):
                    if not message.video or not self._message_contains_all_keywords(message):
                        continue

                    video_id = self._make_video_id(message)
                    if video_id in existing_ids:
                        continue

                    self._log.debug(f"Found new video to download: {video_id}")
                    task = self._download_and_process_video(message, channel, semaphore)
                    tasks.append(task)

            except Exception as e:
                self._log.exception(f"An error occurred while iterating messages in channel '{self._cfg.search.channel_id}': {e}")

            if not tasks:
                self._log.info("No new videos found to download.")
            else:
                self._log.info(
                    f"Found {len(tasks)} new videos. Starting concurrent download (up to {self._cfg.app.download_at_same_time_size} at a time)...")
                results = await asyncio.gather(*tasks)
                download_count = sum(1 for res in results if res)
                self._log.info(f"Finished download session. Successfully downloaded {download_count} new videos.")

        self._log.info("Process finished. Client has disconnected.")
