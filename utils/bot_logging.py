import logging
import sys

from pathlib import Path
from logging.handlers import RotatingFileHandler


LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)

FORMATTER = logging.Formatter(
    fmt='[%(asctime)s] - [%(name)s] - [%(levelname)s] - %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S'
)


def setup_logging(
        name: str = 'bot',
        log_file: str = 'bot.log',
        level: int = logging.INFO,
        max_bytes: int = 2 ** 23 * 10,  # 10 MB
        backup_count: int = 5
) -> logging.Logger:
    """Настройка логирования бота

    Args:
        name: имя логгера
        log_file: имя файла для логов
        level: уровень логирования
        max_bytes: максимальный размер файла для ротации
        backup_count: количество бэкап файлов
    """

    logger = logging.getLogger(name)
    logger.setLevel(level)

    logger.handlers.clear()

    file_handler = RotatingFileHandler(
        filename=LOG_DIR / log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )

    file_handler.setFormatter(FORMATTER)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    """
    logger.info("=" * 60)
    logger.info("Логирование инициализировано")
    logger.info(f"Логи сохраняются в {LOG_DIR / log_file}")
    logger.info(f"Уровень лоирования: {logging.getLevelName(level)}")
    logger.info("=" * 60)
    """

    return logger


def get_logger(name: str = 'bot') -> logging.Logger:
    """Получить настроенный логгер"""

    return logging.getLogger('TimeTracker').getChild(name)
