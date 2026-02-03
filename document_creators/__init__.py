"""
Модуль для создания Word документов с фотографиями в таблицах.
"""

from .constants import SIZE_OPTIONS
from .utils import (
    compress_image,
    calculate_auto_size,
    split_into_pages,
    calculate_pages_info,
    get_size_option_name,
)
from .messages import MessageGenerator
from .document_base import (
    create_single_page_document,
    create_document_with_table,
    set_table_borders,
)
from .document_creator import (
    DocumentCreator,
    TempFileManager,
    cleanup_old_temp_files,
    cleanup_all_temp_files,
)

__all__ = [
    'SIZE_OPTIONS',
    'compress_image',
    'calculate_auto_size',
    'split_into_pages',
    'calculate_pages_info',
    'get_size_option_name',
    'MessageGenerator',
    'create_single_page_document',
    'create_document_with_table',
    'set_table_borders',
    'DocumentCreator',
    'TempFileManager',
    'cleanup_old_temp_files',
    'cleanup_all_temp_files',
]

message_generator = MessageGenerator()