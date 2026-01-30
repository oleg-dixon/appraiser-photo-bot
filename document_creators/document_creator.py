import io
import logging
import tempfile
import os
import shutil
import atexit
import threading
from datetime import datetime, timedelta
from typing import List, Optional, Set
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image

from .constants import SIZE_OPTIONS
from .utils import split_into_pages, calculate_auto_size
from .document_base import set_table_borders, create_single_page_document

logger = logging.getLogger(__name__)


class TempFileManager:
    """Менеджер временных файлов с автоматической очисткой."""
    
    _instance = None
    _lock = threading.Lock()
    _temp_files: Set[str] = set()
    _temp_dirs: Set[str] = set()
    _cleanup_thread = None
    _stop_cleanup = threading.Event()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TempFileManager, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Инициализирует менеджер временных файлов."""
        self.base_temp_dir = tempfile.mkdtemp(prefix="photo_bot_")
        self._temp_dirs.add(self.base_temp_dir)
        logger.info(f"Создана базовая временная директория: {self.base_temp_dir}")
        
        # Регистрируем очистку при выходе
        atexit.register(self.cleanup_all)
        
        # Запускаем фоновую очистку
        self._start_background_cleanup()
    
    def create_temp_file(self, suffix: str = ".docx") -> str:
        """Создает временный файл и регистрирует его для очистки."""
        temp_file = tempfile.mktemp(suffix=suffix, dir=self.base_temp_dir)
        self._temp_files.add(temp_file)
        logger.debug(f"Создан временный файл: {temp_file}")
        return temp_file
    
    def create_temp_dir(self, prefix: str = "temp_") -> str:
        """Создает временную директорию и регистрирует ее для очистки."""
        temp_dir = tempfile.mkdtemp(prefix=prefix, dir=self.base_temp_dir)
        self._temp_dirs.add(temp_dir)
        logger.debug(f"Создана временная директория: {temp_dir}")
        return temp_dir
    
    def register_temp_file(self, filepath: str):
        """Регистрирует существующий файл для очистки."""
        if os.path.exists(filepath):
            self._temp_files.add(filepath)
    
    def unregister_temp_file(self, filepath: str):
        """Удаляет файл из списка отслеживаемых."""
        self._temp_files.discard(filepath)
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """Очищает старые временные файлы."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        files_to_remove = []
        for filepath in self._temp_files.copy():
            try:
                if os.path.exists(filepath):
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_mtime < cutoff_time:
                        files_to_remove.append(filepath)
                else:
                    files_to_remove.append(filepath)
            except Exception as e:
                logger.warning(f"Ошибка при проверке файла {filepath}: {e}")
                files_to_remove.append(filepath)
        
        # Удаляем старые файлы
        for filepath in files_to_remove:
            self._delete_file_safe(filepath)
            self._temp_files.discard(filepath)
        
        # Очищаем пустые директории
        dirs_to_remove = []
        for dirpath in self._temp_dirs.copy():
            if dirpath != self.base_temp_dir:  # Не удаляем базовую директорию
                try:
                    if not os.listdir(dirpath):  # Директория пуста
                        dirs_to_remove.append(dirpath)
                except Exception as e:
                    logger.warning(f"Ошибка при проверке директории {dirpath}: {e}")
        
        for dirpath in dirs_to_remove:
            self._delete_dir_safe(dirpath)
            self._temp_dirs.discard(dirpath)
        
        if files_to_remove or dirs_to_remove:
            logger.info(f"Очищено {len(files_to_remove)} файлов и {len(dirs_to_remove)} директорий")
    
    def _delete_file_safe(self, filepath: str):
        """Безопасно удаляет файл."""
        try:
            os.unlink(filepath)
            logger.debug(f"Удален файл: {filepath}")
        except Exception as e:
            logger.warning(f"Не удалось удалить файл {filepath}: {e}")
    
    def _delete_dir_safe(self, dirpath: str):
        """Безопасно удаляет директорию."""
        try:
            shutil.rmtree(dirpath, ignore_errors=True)
            logger.debug(f"Удалена директория: {dirpath}")
        except Exception as e:
            logger.warning(f"Не удалось удалить директорию {dirpath}: {e}")
    
    def _start_background_cleanup(self):
        """Запускает фоновую очистку."""
        def cleanup_worker():
            while not self._stop_cleanup.is_set():
                try:
                    self.cleanup_old_files(max_age_hours=1)  # Очищаем файлы старше 1 часа
                except Exception as e:
                    logger.error(f"Ошибка в фоновой очистке: {e}")
                
                # Ждем 30 минут до следующей очистки
                self._stop_cleanup.wait(timeout=1800)  # 30 минут
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.info("Запущена фоновая очистка временных файлов")
    
    def stop_background_cleanup(self):
        """Останавливает фоновую очистку."""
        self._stop_cleanup.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
    
    def cleanup_all(self):
        """Очищает все временные файлы и директории."""
        logger.info("Начинаю полную очистку временных файлов...")
        
        # Останавливаем фоновую очистку
        self.stop_background_cleanup()
        
        # Удаляем все файлы
        for filepath in self._temp_files.copy():
            self._delete_file_safe(filepath)
        
        # Удаляем все директории (кроме базовой)
        for dirpath in self._temp_dirs.copy():
            if dirpath != self.base_temp_dir:
                self._delete_dir_safe(dirpath)
        
        # Удаляем базовую директорию
        if os.path.exists(self.base_temp_dir):
            self._delete_dir_safe(self.base_temp_dir)
        
        self._temp_files.clear()
        self._temp_dirs.clear()
        logger.info("Полная очистка временных файлов завершена")


class DocumentCreator:
    """Создатель Word документов с таблицами."""
    
    def __init__(
        self, 
        title: Optional[str] = None,
        rows: int = 1,
        cols: int = 1,
        size_option: str = 'medium',
        use_temp_files: bool = True  # Использовать временные файлы
    ):
        self.title = title
        self.rows = rows
        self.cols = cols
        self.size_option = size_option
        self.use_temp_files = use_temp_files
        self.temp_manager = TempFileManager()
        self._photo_counter = 0
    
    def _setup_page(self, doc: Document):
        """Настраивает параметры страницы."""
        section = doc.sections[0]
        section.left_margin = Cm(1.5)
        section.right_margin = Cm(1.5)
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
    
    def create_multi_page_document(self, photos: List[bytes]) -> bytes:
        """
        Создает многостраничный документ.
        
        Args:
            photos: Список байтов фотографий
            
        Returns:
            Байты готового документа
        """
        # Если одна страница - используем базовую функцию
        photos_per_page = self.rows * self.cols
        if photos_per_page <= 0 or len(photos) <= photos_per_page:
            return self._create_single_page(photos)
        
        # Для многостраничных используем сложную логику
        photos_count = len(photos)
        use_file_method = self.use_temp_files and photos_count > 10  # Для >10 фото используем файлы
        
        if use_file_method:
            return self._create_with_temp_file(photos)
        else:
            return self._create_in_memory(photos)
    
    def _create_single_page(self, photos: List[bytes]) -> bytes:
        """Создает одностраничный документ."""
        doc = create_single_page_document(
            photos=photos,
            rows=self.rows,
            cols=self.cols,
            table_title=self.title,
            image_size_option=self.size_option
        )
        
        buffer = io.BytesIO()
        doc.save(buffer)
        return buffer.getvalue()
    
    def _create_in_memory(self, photos: List[bytes]) -> bytes:
        """Создает документ в памяти."""
        try:
            doc = Document()
            
            # Устанавливаем базовый стиль для всего документа
            style = doc.styles['Normal']
            style.font.name = 'Times New Roman'
            style.font.size = Pt(12)
            
            self._setup_page(doc)
            
            photo_pages = split_into_pages(photos, self.rows, self.cols)
            total_pages = len(photo_pages)
            
            logger.info(f"Создаю документ в памяти: {len(photos)} фото, "
                       f"{self.rows}×{self.cols}, {total_pages} страниц")
            
            for page_num, page_photos in enumerate(photo_pages, 1):
                if page_num > 1:
                    doc.add_page_break()
                
                if total_pages > 1:
                    self._add_page_title_to_doc(doc, page_num, total_pages)
                
                self._create_page_table_in_doc(doc, page_photos, page_num, total_pages)
            
            buffer = io.BytesIO()
            doc.save(buffer)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Ошибка при создании в памяти: {e}")
            return self._create_with_temp_file(photos)
    
    def _create_with_temp_file(self, photos: List[bytes]) -> bytes:
        """Создает документ через временный файл."""
        temp_file = None
        try:
            # Создаем временный файл через менеджер
            temp_file = self.temp_manager.create_temp_file(suffix=".docx")
            
            # Создаем и сохраняем документ
            self._create_and_save_to_file(photos, temp_file)
            
            # Читаем файл
            with open(temp_file, 'rb') as f:
                document_bytes = f.read()
            
            file_size = len(document_bytes) / 1024 / 1024
            logger.info(f"Документ создан через файл: {file_size:.2f} MB, файл: {temp_file}")
            
            return document_bytes
            
        except Exception as e:
            logger.error(f"Ошибка при создании через файл: {e}")
            raise
        finally:
            # Файл будет удален менеджером автоматически
            if temp_file:
                logger.debug(f"Временный файл зарегистрирован для очистки: {temp_file}")
    
    def _create_and_save_to_file(self, photos: List[bytes], filepath: str):
        """Создает документ и сохраняет в файл."""
        doc = Document()
        
        # Устанавливаем базовый стиль для всего документа
        style = doc.styles['Normal']
        style.font.name = 'Times New Roman'
        style.font.size = Pt(12)
        
        self._setup_page(doc)
        
        photo_pages = split_into_pages(photos, self.rows, self.cols)
        total_pages = len(photo_pages)
        
        logger.info(f"Сохраняю документ в файл {filepath}: {len(photos)} фото, "
                   f"{self.rows}×{self.cols}, {total_pages} страниц")
        
        for page_num, page_photos in enumerate(photo_pages, 1):
            if page_num > 1:
                doc.add_page_break()
            
            if total_pages > 1:
                self._add_page_title_to_doc(doc, page_num, total_pages)
            
            self._create_page_table_in_doc(doc, page_photos, page_num, total_pages)
        
        # Сохраняем в файл
        doc.save(filepath)
        
        file_size = os.path.getsize(filepath) / 1024 / 1024
        logger.info(f"Документ сохранен в файл: {file_size:.2f} MB")
    
    def _add_title_to_doc(self, doc: Document):
        """Добавляет заголовок документа."""
        if self.title:
            title_paragraph = doc.add_paragraph()
            title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

            run = title_paragraph.add_run(self.title)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(12)
            run.font.bold = True  # Можно сделать жирным для выделения
            run.font.color.rgb = RGBColor(0, 0, 0)  # Черный
        
        doc.add_paragraph()  # Пустая строка после заголовка
    
    def _add_page_title_to_doc(self, doc: Document, page_num: int, total_pages: int):
        """Добавляет заголовок страницы."""
        if self.title and total_pages > 1:
            page_title = f"{self.title} - Страница {page_num} из {total_pages}"
        elif total_pages > 1:
            page_title = f"Страница {page_num} из {total_pages}"
        else:
            return
        
        # Используем правильный формат для заголовка страницы
        title_paragraph = doc.add_paragraph()
        title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        run = title_paragraph.add_run(page_title)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 0, 0)
        
        doc.add_paragraph()  # Пустая строка
    
    def _create_page_table_in_doc(self, doc: Document, photos: List[bytes], page_num: int, total_pages: int):
        """Создает таблицу для страницы."""
        logger.info(f"Создаю таблицу для страницы {page_num}/{total_pages}, фото: {len(photos)}")

        actual_rows = self.rows
        actual_cols = self.cols

        if page_num == total_pages and len(photos) < self.rows * self.cols:
            actual_rows = min(self.rows, (len(photos) + self.cols - 1) // self.cols)
            actual_cols = min(self.cols, len(photos))

        logger.info(f"Размер таблицы: {actual_rows}×{actual_cols}")

        # Создаем таблицу
        table = doc.add_table(rows=actual_rows, cols=actual_cols)

        # Убираем отступы в ячейках
        for row in table.rows:
            for cell in row.cells:
                cell.paragraphs[0].paragraph_format.space_after = Pt(0)
                cell.paragraphs[0].paragraph_format.space_before = Pt(0)
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        photo_width = self._get_photo_width_for_table(actual_rows, actual_cols)
        logger.info(f"Ширина фото: {photo_width.cm} см")

        for row_idx in range(actual_rows):
            row = table.rows[row_idx]
            row.height_rule = 1  # Автоматическая высота

            for col_idx in range(actual_cols):
                cell = row.cells[col_idx]

                photo_index = row_idx * actual_cols + col_idx
                if photo_index < len(photos):
                    global_index = self._photo_counter + photo_index
                    logger.debug(f"Добавляю фото {global_index + 1} в ячейку [{row_idx},{col_idx}]")
                    self._insert_photo_to_cell_in_doc(
                        cell, 
                        photos[photo_index], 
                        photo_width, 
                        global_index
                    )
                else:
                    logger.debug(f"Пустая ячейка [{row_idx},{col_idx}]")
                    cell.text = ""

        # Обновляем счетчик
        self._photo_counter += len(photos)
        
        # Убираем границы таблицы
        set_table_borders(table, visible=False)
    
    def _insert_photo_to_cell_in_doc(self, cell, photo_bytes: bytes, width: Cm, index: int):
        """Вставляет фото в ячейку."""
        try:
            logger.debug(f"Вставляю фото {index + 1}, размер байт: {len(photo_bytes)}")

            # Проверяем, что есть данные
            if not photo_bytes or len(photo_bytes) == 0:
                logger.warning(f"Пустые байты для фото {index}")
                cell.text = f"Фото {index + 1}\n(нет данных)"
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                return

            # Проверяем размер фото
            if len(photo_bytes) > 5 * 1024 * 1024:  # >5MB
                logger.warning(f"Фото {index + 1} слишком большое: {len(photo_bytes)/1024/1024:.1f} MB")
                # Попробуем сжать сильнее

            # Создаем BytesIO из байтов
            img_buffer = io.BytesIO(photo_bytes)

            # Пытаемся открыть изображение для проверки
            try:
                img = Image.open(img_buffer)
                original_format = img.format
                original_size = img.size

                logger.debug(f"Открыто изображение {index + 1}: {original_format}, {original_size}, {img.mode}")

                # Конвертируем в RGB если нужно
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Создаем белый фон для прозрачных изображений
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                    logger.debug(f"Конвертировано из {img.mode} в RGB")
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                    logger.debug(f"Конвертировано из {img.mode} в RGB")

                # Масштабируем если изображение слишком большое
                max_pixels = 2000 * 2000  # Максимум 4MP
                if img.width * img.height > max_pixels:
                    # Вычисляем коэффициент масштабирования
                    scale_factor = (max_pixels / (img.width * img.height)) ** 0.5
                    new_width = int(img.width * scale_factor)
                    new_height = int(img.height * scale_factor)

                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    logger.debug(f"Масштабировано до: {new_width}x{new_height}")

                # Сохраняем в JPEG формат с сильным сжатием для документа
                jpeg_buffer = io.BytesIO()

                # Определяем качество в зависимости от размера
                quality = 65  # Среднее качество для документов

                # Для очень больших исходных фото сжимаем сильнее
                if len(photo_bytes) > 2 * 1024 * 1024:  # >2MB
                    quality = 55
                elif len(photo_bytes) > 1 * 1024 * 1024:  # >1MB
                    quality = 60

                img.save(jpeg_buffer, format='JPEG', quality=quality, optimize=True)
                jpeg_buffer.seek(0)  # Важно: перематываем в начало!

                # Проверяем размер после сжатия
                compressed_size = len(jpeg_buffer.getvalue())
                compression_ratio = compressed_size / len(photo_bytes) if len(photo_bytes) > 0 else 0

                logger.debug(f"Сжатие фото {index + 1}: {len(photo_bytes)} → {compressed_size} "
                            f"({compression_ratio*100:.1f}%), качество: {quality}")

                # Если сжатие не дало результата или увеличило размер
                if compressed_size >= len(photo_bytes) and compression_ratio > 0.9:
                    logger.warning(f"Сжатие неэффективно для фото {index + 1}")
                    # Закрываем JPEG буфер и используем оригинал
                    jpeg_buffer.close()
                    img_buffer.seek(0)
                else:
                    # Закрываем оригинальный буфер
                    img_buffer.close()
                    # Используем сжатый JPEG буфер
                    img_buffer = jpeg_buffer

            except Exception as img_error:
                logger.warning(f"Ошибка при обработке изображения {index + 1}, пробуем как есть: {img_error}")
                # Если не удалось обработать, используем оригинальные байты
                img_buffer.seek(0)

            # Вставляем фото в ячейку
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Очищаем ячейку от существующего содержимого
            for p in cell.paragraphs:
                for run in p.runs:
                    run.clear()

            # Добавляем фото
            run = paragraph.add_run()

            try:
                # ВАЖНО: передаем BytesIO объект, не его содержимое
                # Сохраняем текущую позицию буфера
                current_pos = img_buffer.tell()
                img_buffer.seek(0)  # Убеждаемся, что в начале

                run.add_picture(img_buffer, width=width)

                logger.debug(f"✅ Фото {index + 1} успешно добавлено, ширина: {width.cm} см")

            except Exception as add_error:
                logger.error(f"Ошибка при добавлении фото {index + 1}: {add_error}")

                # Пробуем альтернативный метод через временный файл
                try:
                    # Закрываем текущий буфер
                    img_buffer.close()

                    # Создаем новый буфер с оригинальными данными
                    temp_buffer = io.BytesIO(photo_bytes)

                    # Пытаемся сохранить в более простом формате
                    try:
                        img = Image.open(temp_buffer)
                        simple_buffer = io.BytesIO()
                        img.save(simple_buffer, format='JPEG', quality=50)  # Очень сильное сжатие
                        simple_buffer.seek(0)
                        temp_buffer = simple_buffer
                    except:
                        temp_buffer.seek(0)

                    # Сохраняем во временный файл
                    temp_file = self.temp_manager.create_temp_file(suffix='.jpg')
                    with open(temp_file, 'wb') as f:
                        f.write(temp_buffer.getvalue())

                    # Очищаем run и пробуем снова
                    run.clear()
                    run.add_picture(temp_file, width=width)

                    logger.debug(f"✅ Фото {index + 1} добавлено через временный файл: {temp_file}")

                    # Закрываем буферы
                    temp_buffer.close()

                except Exception as temp_error:
                    logger.error(f"Не удалось добавить фото {index + 1} даже через временный файл: {temp_error}")
                    cell.text = f"Фото {index + 1}\n(ошибка вставки)"
                    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Закрываем буфер
            try:
                img_buffer.close()
            except:
                pass

        except Exception as e:
            logger.error(f"Критическая ошибка при вставке фото {index + 1}: {e}", exc_info=True)
            cell.text = f"Фото {index + 1}\n(ошибка)"
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    def _get_photo_width_for_table(self, actual_rows: int, actual_cols: int) -> Cm:
        """Возвращает ширину фото."""
        if self.size_option == 'auto':
            photo_size_cm = calculate_auto_size(actual_rows, actual_cols)
            return Cm(photo_size_cm[0])
        elif self.size_option in SIZE_OPTIONS:
            photo_size_cm = SIZE_OPTIONS[self.size_option]
            return Cm(photo_size_cm[0])
        else:
            return Cm(5.0)
    
    # Методы для обратной совместимости
    def add_title(self):
        """Для обратной совместимости."""
        pass
    
    def create_table(self, photos: List[bytes]) -> bytes:
        """Старый метод для обратной совместимости."""
        logger.warning("Используется старый метод create_table")
        return self.create_multi_page_document(photos)


# Функции для ручного управления очисткой
def cleanup_old_temp_files(max_age_hours: int = 24):
    """Очищает старые временные файлы."""
    manager = TempFileManager()
    manager.cleanup_old_files(max_age_hours)

def cleanup_all_temp_files():
    """Очищает все временные файлы."""
    manager = TempFileManager()
    manager.cleanup_all()