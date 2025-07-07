# download-tg

A utility for downloading restricted videos and audios from private Telegram channels.

## Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
2. Activate the environment:
   ```bash
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```

## Usage

Run the application with your configuration file:

```bash
python run.py /path/to/your/config.yaml
```

- On the first run, you will need to enter the authentication code from the Telegram app and your password.
- After that, a session file will be saved and you won't need to enter anything again.

## Configuration

- The configuration file should be in YAML format. See the example: `configs/cfg.yaml`.
- To get your `api_id` and `api_hash`, go to [https://my.telegram.org/](https://my.telegram.org/) and create your own
  application.
- **The `channel_id` must be specified as a number, without the '-' sign.**
- You can extract the `channel_id` from the URL in the [web version of Telegram](https://web.telegram.org/k/).

## Exporting a Report

To export the list of downloaded files to a CSV file:

   ```bash
   sqlite3 -header -csv YOUR_SQLITE_DB_FILE.db "SELECT * FROM downloaded_videos;" > data.csv
   ```
