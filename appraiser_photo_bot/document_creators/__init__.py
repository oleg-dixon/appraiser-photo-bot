"""
Модуль для создания Word документов с фотографиями в таблицах.
"""

from .constants import SIZE_OPTIONS
from .document_base import (
    create_document_with_table,
    create_single_page_document,
    set_table_borders,
)
from .document_creator import DocumentCreator
from .messages import MessageGenerator
from .temp_manager import (
    TempFileManager,
    cleanup_all_temp_files,
    cleanup_old_temp_files,
)
from .utils import (
    calculate_auto_size,
    calculate_pages_info,
    compress_image,
    get_size_option_name,
    split_into_pages,
)

__all__ = [
    "SIZE_OPTIONS",
    "compress_image",
    "calculate_auto_size",
    "split_into_pages",
    "calculate_pages_info",
    "get_size_option_name",
    "MessageGenerator",
    "create_single_page_document",
    "create_document_with_table",
    "set_table_borders",
    "DocumentCreator",
    "TempFileManager",
    "cleanup_old_temp_files",
    "cleanup_all_temp_files",
]

message_generator = MessageGenerator()
