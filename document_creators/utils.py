"""
Утилитные функции для работы с изображениями и вычислений.
"""

import io
import logging
from typing import Tuple, List
from PIL import Image

from .constants import SIZE_OPTIONS, MAX_IMAGE_SIZE, DEFAULT_IMAGE_QUALITY

logger = logging.getLogger(__name__)


def compress_image(image_bytes: bytearray, quality: int = DEFAULT_IMAGE_QUALITY, 
                   max_size: int = MAX_IMAGE_SIZE) -> bytes:
    """
    Сжимает изображение до указанного качества и размера.
    Алгоритм:
    1. Всегда уменьшаем размер если больше max_size
    2. JPEG оптимизируем с указанным качеством
    3. PNG/WEBP конвертируем в JPEG только если это уменьшит размер
    4. Всегда возвращаем самый маленький вариант
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        original_format = image.format or 'JPEG'
        original_size = len(image_bytes)
        
        # Масштабируем если слишком большое
        width, height = image.size
        if max(width, height) > max_size:
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Масштабирование: {width}x{height} → {new_width}x{new_height}")
        
        # Пробуем разные варианты сохранения
        variants = []
        
        # Вариант 1: оригинальный формат с оптимизацией
        buffer1 = io.BytesIO()
        image.save(buffer1, format=original_format, optimize=True)
        variants.append((len(buffer1.getvalue()), buffer1.getvalue(), original_format))
        
        # Вариант 2: JPEG (если не JPEG уже)
        if original_format != 'JPEG':
            # Конвертируем в RGB для JPEG
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image_for_jpeg = image.convert('RGBA')
                else:
                    image_for_jpeg = image
                background.paste(image_for_jpeg, mask=image_for_jpeg.split()[-1] if image_for_jpeg.mode == 'RGBA' else None)
                image_for_jpeg = background
            elif image.mode != 'RGB':
                image_for_jpeg = image.convert('RGB')
            else:
                image_for_jpeg = image
            
            buffer2 = io.BytesIO()
            image_for_jpeg.save(buffer2, format='JPEG', quality=quality, optimize=True, progressive=True)
            variants.append((len(buffer2.getvalue()), buffer2.getvalue(), 'JPEG'))
        
        # Вариант 3: JPEG с более низким качеством (если оригинал JPEG)
        elif original_format == 'JPEG':
            buffer3 = io.BytesIO()
            image.save(buffer3, format='JPEG', quality=max(50, quality-20), optimize=True, progressive=True)
            variants.append((len(buffer3.getvalue()), buffer3.getvalue(), 'JPEG_compressed'))
        
        # Выбираем самый маленький вариант
        variants.sort(key=lambda x: x[0])
        best_size, best_bytes, best_format = variants[0]
        
        logger.info(f"Лучший вариант: {original_format} → {best_format}, "
                   f"{original_size} → {best_size} ({best_size/original_size*100:.1f}%)")
        
        # Если лучший вариант не намного меньше (менее 5%), возвращаем оригинал
        if best_size >= original_size * 0.95:
            logger.info(f"Уменьшение менее 5%, возвращаю оригинал")
            return bytes(image_bytes)
        
        return best_bytes
        
    except Exception as e:
        logger.error(f"Ошибка при сжатии изображения: {e}", exc_info=True)
        return bytes(image_bytes)


def calculate_auto_size(
    rows: int, 
    cols: int, 
    page_width_cm: float = 17.0, 
    page_height_cm: float = 25.0
) -> Tuple[float, float]:
    """
    Автоматически вычисляет оптимальный размер фото для таблицы.
    
    Args:
        rows: количество строк в таблице
        cols: количество столбцов в таблице
        page_width_cm: ширина доступной области страницы (см)
        page_height_cm: высота доступной области страницы (см)
    
    Returns:
        Кортеж (ширина_см, высота_см)
    """
    max_cell_width = page_width_cm / cols
    max_cell_height = page_height_cm / rows
    
    # Берем минимальное значение с небольшим запасом
    size_cm = min(max_cell_width, max_cell_height) * 0.9
    
    # Ограничиваем разумными пределами
    size_cm = max(2.0, min(size_cm, 10.0))
    
    return (size_cm, size_cm)


def split_into_pages(photos: List[bytes], rows: int, cols: int) -> List[List[bytes]]:
    """
    Разбивает список фото на страницы по rows×cols фото на страницу.
    
    Args:
        photos: список байтов фотографий
        rows: строк на странице
        cols: столбцов на странице
    
    Returns:
        Список страниц (списков фото)
    """
    photos_per_page = rows * cols
    if photos_per_page <= 0:
        return [photos]
    
    pages = []
    for i in range(0, len(photos), photos_per_page):
        page = photos[i:i + photos_per_page]
        pages.append(page)
    
    return pages


def calculate_pages_info(photos_count: int, rows: int, cols: int) -> dict:
    """
    Вычисляет информацию о страницах документа.
    
    Args:
        photos_count: общее количество фотографий
        rows: строк в таблице на странице
        cols: столбцов в таблице на странице
    
    Returns:
        Словарь с информацией о страницах
    """
    photos_per_page = rows * cols
    total_pages = (photos_count + photos_per_page - 1) // photos_per_page
    photos_on_last_page = photos_count % photos_per_page
    if photos_on_last_page == 0 and photos_count > 0:
        photos_on_last_page = photos_per_page
    
    return {
        'total_photos': photos_count,
        'rows': rows,
        'cols': cols,
        'photos_per_page': photos_per_page,
        'total_pages': total_pages,
        'photos_on_last_page': photos_on_last_page
    }


def get_size_option_name(size_key: str) -> str:
    """
    Возвращает читаемое название размера.
    
    Args:
        size_key: ключ размера ('small', 'medium', 'large', 'auto')
    
    Returns:
        Читаемое название размера
    """
    if size_key == 'auto':
        return "автоматический"
    elif size_key in SIZE_OPTIONS:
        size_cm = SIZE_OPTIONS[size_key][0]
        return f"{size_cm} см"
    return "неизвестный"