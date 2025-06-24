## download-tg

Утилита для загрузки видео из приватных каналов в телеграмме.

## Установка зависимостей

```
pytnon -m venv venv
pytno -m pip install -r requirements.txt
```

## Использование

```bash
python run.py /path/to/your/config.yaml
```

При первом запуске нужно будет ввести код из аппы для аутентификации и пароль. Длаее сохранится файл с сессией и ничего
не нужно будет вводить.
Пример конфиг файла: `configs/cfg.yaml`

Для получения api_id и api_hash нужно зайти на https://my.telegram.org/, создать свое приложение.
При создании приложения нужно заполнить все поля. **channel_id указать числом, без знака -.**

## Выгрузка отчета

```bash
 sqlite3 local_db.db 

sqlite> .headers on
sqlite> .mode csv
sqlite> .output data.csv
sqlite> select * from downloaded_videos;
sqlite> .quit
```

