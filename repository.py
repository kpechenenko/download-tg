import asyncio
import dataclasses
import datetime
import logging
import os
import sqlite3
import typing as tp


@dataclasses.dataclass
class DownloadedVideo:
    """
    Represents a video record in the database.
    """
    id: str
    channel_id: int
    message_id: str
    text: str
    filename: str
    created: datetime.datetime


class SqliteVideoDownloadHistoryRepository:
    """
    An asynchronous repository for storing video download history in an SQLite database.
    It safely handles synchronous database operations in an asyncio environment.
    """

    def __init__(self, filename: str):
        """
        Initializes the repository.

        :param filename: Path to the SQLite3 database file.
        """
        self._filename = filename
        self._conn: tp.Optional[sqlite3.Connection] = None
        self._lock = asyncio.Lock()  # Lock to ensure thread-safe connection handling.
        self._log = logging.getLogger(__name__)

    def _connect_and_init_db(self) -> sqlite3.Connection:
        """
        Establishes a synchronous connection to the SQLite database and initializes the schema if it does not exist.

        This method is intended to be executed in a separate thread to avoid blocking the asyncio event loop.

        :return: sqlite3.Connection - An open SQLite database connection with the required schema initialized.
        """
        self._log.info(f"Connecting to database at {self._filename}")
        conn = sqlite3.connect(self._filename, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS downloaded_videos (
                id TEXT PRIMARY KEY,
                channel_id INT NOT NULL,
                message_id TEXT NOT NULL,
                text TEXT NOT NULL,
                filename TEXT NOT NULL,
                created TEXT NOT NULL
            )
            """
        )
        conn.commit()
        cursor.close()
        self._log.info("Database connection and schema initialization complete.")
        return conn

    async def _get_connection(self) -> sqlite3.Connection:
        """
        Asynchronously gets or creates a database connection.

        Ensures that the connection is established only once.

        :return: sqlite3.Connection - An open SQLite database connection with the required schema initialized.
        """
        async with self._lock:
            if self._conn is None:
                self._conn = await asyncio.to_thread(self._connect_and_init_db)
            return self._conn

    async def open_conn(self) -> None:
        """
        Explicitly opens and prepares the connection to the database.

        :return:
        """
        await self._get_connection()

    async def close_conn(self) -> None:
        """
        Closes the connection to the database.

        :return:
        """
        async with self._lock:
            if self._conn is not None:
                self._log.info("Closing database connection.")
                await asyncio.to_thread(self._conn.close)
                self._conn = None

    def _write_sync(self, conn: sqlite3.Connection, v: DownloadedVideo) -> None:
        """
        Synchronous worker for writing a video record.

        :param conn: The SQLite database connection.
        :param v: The DownloadedVideo object to save.
        :return:
        """
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO downloaded_videos (id, channel_id, message_id, text, filename, created)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (v.id, v.channel_id, v.message_id, v.text, v.filename, v.created.isoformat()),
        )
        conn.commit()
        cursor.close()

    async def write(self, v: DownloadedVideo) -> None:
        """
        Asynchronously saves a new video record to the database.

        :param v: The DownloadedVideo object to save.
        :return:
        """
        conn = await self._get_connection()
        await asyncio.to_thread(self._write_sync, conn, v)

    def _get_video_ids_sync(self, conn: sqlite3.Connection, channel_id: int) -> tp.Set[str]:
        """
        Synchronous worker for retrieving video IDs for a given channel.

        :param conn: The SQLite database connection.
        :param channel_id: The channel ID to query for.
        :return: A set of unique video ID strings.
        """
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM downloaded_videos WHERE channel_id = ?", (channel_id,))
        rows = cursor.fetchall()
        cursor.close()

        ids = {os.path.splitext(os.path.basename(row["filename"]))[0] for row in rows}
        return ids

    async def get_video_ids(self, channel_id: int) -> tp.Set[str]:
        """
        Asynchronously retrieves the set of unique video identifiers for a given channel.
        This is used to prevent re-downloading existing videos.

        :param channel_id: The channel ID to query for.
        :return: A set of unique video ID strings.
        """
        conn = await self._get_connection()
        return await asyncio.to_thread(self._get_video_ids_sync, conn, channel_id)

    async def _init_schema_if_necessary(self) -> None:
        """
        This method is retained for backward compatibility. 
        Schema initialization is now automatically managed by _get_connection, 
        so this function simply ensures a database connection is established.

        :return:
        """
        await self._get_connection()
