"""Создатель Word документов с таблицами."""

import io
import logging
from typing import List, Optional

from docx import Document

from .temp_manager import TempFileManager
from .utils import compress_photos_for_document
from .document_base import create_single_page_document, create_multi_page_document

logger = logging.getLogger(__name__)


class DocumentCreator:
    """Упрощенный создатель документов."""

    def __init__(
        self,
        title: Optional[str] = None,
        rows: int = 1,
        cols: int = 1,
        size_option: str = "medium",
        use_temp_files: bool = True,
    ) -> None:
        self.title: Optional[str] = title
        self.rows: int = rows
        self.cols: int = cols
        self.size_option: str = size_option
        self.use_temp_files: bool = use_temp_files
        self.temp_manager: TempFileManager = TempFileManager()

    def create_document(self, photos: List[bytes]) -> bytes:
        """Создает документ с фотографиями."""
        compressed_photos: List[bytes] = compress_photos_for_document(photos)

        photos_per_page: int = self.rows * self.cols
        if photos_per_page <= 0 or len(compressed_photos) <= photos_per_page:
            return self._create_single_page(compressed_photos)

        return self._create_multi_page(compressed_photos)

    def _create_single_page(self, photos: List[bytes]) -> bytes:
        """Создает одностраничный документ."""
        doc: Document = create_single_page_document(
            photos=photos,
            rows=self.rows,
            cols=self.cols,
            table_title=self.title,
            image_size_option=self.size_option,
        )
        buffer: io.BytesIO = io.BytesIO()
        doc.save(buffer)
        return buffer.getvalue()

    def _create_multi_page(self, photos: List[bytes]) -> bytes:
        """Создает многостраничный документ."""
        if self.use_temp_files and len(photos) > 10:
            return self._create_via_temp_file(photos)
        else:
            return self._create_in_memory(photos)

    def _create_in_memory(self, photos: List[bytes]) -> bytes:
        """Создает документ в памяти."""
        try:
            doc: Document = create_multi_page_document(
                photos=photos,
                rows=self.rows,
                cols=self.cols,
                table_title=self.title,
                image_size_option=self.size_option,
            )
            buffer: io.BytesIO = io.BytesIO()
            doc.save(buffer)
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Ошибка создания в памяти: {e}")
            return self._create_via_temp_file(photos)

    def _create_via_temp_file(self, photos: List[bytes]) -> bytes:
        """Создает документ через временный файл."""
        temp_file: Optional[str] = None
        try:
            temp_file = self.temp_manager.create_temp_file(suffix=".docx")

            doc: Document = create_multi_page_document(
                photos=photos,
                rows=self.rows,
                cols=self.cols,
                table_title=self.title,
                image_size_option=self.size_option,
            )
            doc.save(temp_file)

            with open(temp_file, "rb") as f:
                document_bytes: bytes = f.read()

            file_size: float = len(document_bytes) / 1024 / 1024
            logger.info(f"Документ создан через файл: {file_size:.2f} MB")

            return document_bytes

        except Exception as e:
            logger.error(f"Ошибка при создании через файл: {e}")
            raise
        finally:
            if temp_file:
                logger.debug(f"Временный файл зарегистрирован: {temp_file}")

    def create_table(self, photos: List[bytes]) -> bytes:
        """Старый метод для обратной совместимости."""
        logger.warning("Используется устаревший метод create_table")
        return self.create_document(photos)
    