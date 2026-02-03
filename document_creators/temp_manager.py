"""Менеджер временных файлов с автоматической очисткой."""

import os
import shutil
import tempfile
import threading
import atexit
import logging
from datetime import datetime, timedelta
from typing import Set, List, Optional

logger = logging.getLogger(__name__)


class TempFileManager:
    """Менеджер временных файлов с автоматической очисткой."""

    _instance: Optional["TempFileManager"] = None
    _lock: threading.Lock = threading.Lock()
    _temp_files: Set[str] = set()
    _temp_dirs: Set[str] = set()
    _cleanup_thread: Optional[threading.Thread] = None
    _stop_cleanup: threading.Event = threading.Event()

    def __new__(cls) -> "TempFileManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance

    def _initialize(self) -> None:
        self.base_temp_dir: str = tempfile.mkdtemp(prefix="photo_bot_")
        self._temp_dirs.add(self.base_temp_dir)
        logger.info(f"Создана базовая временная директория: {self.base_temp_dir}")

        atexit.register(self.cleanup_all)
        self._start_background_cleanup()

    def create_temp_file(self, suffix: str = ".docx") -> str:
        temp_file: str = tempfile.mktemp(suffix=suffix, dir=self.base_temp_dir)
        self._temp_files.add(temp_file)
        logger.debug(f"Создан временный файл: {temp_file}")
        return temp_file

    def create_temp_dir(self, prefix: str = "temp_") -> str:
        temp_dir: str = tempfile.mkdtemp(prefix=prefix, dir=self.base_temp_dir)
        self._temp_dirs.add(temp_dir)
        logger.debug(f"Создана временная директория: {temp_dir}")
        return temp_dir

    def register_temp_file(self, filepath: str) -> None:
        if os.path.exists(filepath):
            self._temp_files.add(filepath)

    def unregister_temp_file(self, filepath: str) -> None:
        self._temp_files.discard(filepath)

    def cleanup_old_files(self, max_age_hours: int = 24) -> None:
        cutoff_time: datetime = datetime.now() - timedelta(hours=max_age_hours)

        files_to_remove: List[str] = []
        for filepath in self._temp_files.copy():
            try:
                if os.path.exists(filepath):
                    file_mtime: datetime = datetime.fromtimestamp(
                        os.path.getmtime(filepath)
                    )
                    if file_mtime < cutoff_time:
                        files_to_remove.append(filepath)
                else:
                    files_to_remove.append(filepath)
            except Exception as e:
                logger.warning(f"Ошибка при проверке файла {filepath}: {e}")
                files_to_remove.append(filepath)

        for filepath in files_to_remove:
            self._delete_file_safe(filepath)
            self._temp_files.discard(filepath)

        dirs_to_remove: List[str] = []
        for dirpath in self._temp_dirs.copy():
            if dirpath != self.base_temp_dir:
                try:
                    if not os.listdir(dirpath):
                        dirs_to_remove.append(dirpath)
                except Exception as e:
                    logger.warning(f"Ошибка при проверке директории {dirpath}: {e}")

        for dirpath in dirs_to_remove:
            self._delete_dir_safe(dirpath)
            self._temp_dirs.discard(dirpath)

        if files_to_remove or dirs_to_remove:
            logger.info(
                f"Очищено {len(files_to_remove)} файлов и {len(dirs_to_remove)} директорий"
            )

    def _delete_file_safe(self, filepath: str) -> None:
        try:
            os.unlink(filepath)
            logger.debug(f"Удален файл: {filepath}")
        except Exception as e:
            logger.warning(f"Не удалось удалить файл {filepath}: {e}")

    def _delete_dir_safe(self, dirpath: str) -> None:
        try:
            shutil.rmtree(dirpath, ignore_errors=True)
            logger.debug(f"Удалена директория: {dirpath}")
        except Exception as e:
            logger.warning(f"Не удалось удалить директорию {dirpath}: {e}")

    def _start_background_cleanup(self) -> None:
        def cleanup_worker() -> None:
            while not self._stop_cleanup.is_set():
                try:
                    self.cleanup_old_files(max_age_hours=1)
                except Exception as e:
                    logger.error(f"Ошибка в фоновой очистке: {e}")
                self._stop_cleanup.wait(timeout=1800)

        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.info("Запущена фоновая очистка временных файлов")

    def stop_background_cleanup(self) -> None:
        self._stop_cleanup.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)

    def cleanup_all(self) -> None:
        logger.info("Начинаю полную очистку временных файлов...")
        self.stop_background_cleanup()

        for filepath in self._temp_files.copy():
            self._delete_file_safe(filepath)

        for dirpath in self._temp_dirs.copy():
            if dirpath != self.base_temp_dir:
                self._delete_dir_safe(dirpath)

        if os.path.exists(self.base_temp_dir):
            self._delete_dir_safe(self.base_temp_dir)

        self._temp_files.clear()
        self._temp_dirs.clear()
        logger.info("Полная очистка временных файлов завершена")


def cleanup_old_temp_files(max_age_hours: int = 24) -> None:
    manager: TempFileManager = TempFileManager()
    manager.cleanup_old_files(max_age_hours)


def cleanup_all_temp_files() -> None:
    manager: TempFileManager = TempFileManager()
    manager.cleanup_all()
    