"""Утилитные функции для работы с изображениями и вычислений."""

import io
import logging
from typing import Tuple, List, Optional, Dict, Union
from PIL import Image

from .constants import SIZE_OPTIONS, MAX_IMAGE_SIZE, DEFAULT_IMAGE_QUALITY

logger = logging.getLogger(__name__)


def compress_image(
    image_bytes: bytes,
    quality: int = DEFAULT_IMAGE_QUALITY,
    max_size: int = MAX_IMAGE_SIZE,
    target_format: str = "JPEG",
) -> bytes:
    """Сжимает изображение до указанного качества и размера."""
    try:
        original_size: int = len(image_bytes)

        with Image.open(io.BytesIO(image_bytes)) as image:
            original_format: Optional[str] = image.format or "JPEG"
            width, height = image.size

            if max(width, height) > max_size:
                new_width: int
                new_height: int
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))

                image = image.resize(
                    (new_width, new_height), Image.Resampling.LANCZOS
                )
                logger.info(
                    f"Масштабирование: {width}x{height} → {new_width}x{new_height}"
                )

            if image.mode in ("RGBA", "LA", "P"):
                background: Image.Image = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                mask: Optional[Image.Image] = None
                if image.mode == "RGBA":
                    mask = image.split()[-1]
                background.paste(image, mask=mask)
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

            output_buffer: io.BytesIO = io.BytesIO()
            image.save(
                output_buffer,
                format=target_format,
                quality=quality,
                optimize=True,
                progressive=True,
            )

            compressed_size: int = len(output_buffer.getvalue())
            compression_ratio: float = compressed_size / original_size

            logger.info(
                f"Сжатие: {original_format} → {target_format}, "
                f"{original_size} → {compressed_size} ({compression_ratio*100:.1f}%)"
            )

            if compression_ratio > 0.95:
                logger.info("Уменьшение менее 5%, возвращаю оригинал")
                return image_bytes

            return output_buffer.getvalue()

    except Exception as e:
        logger.error(f"Ошибка при сжатии изображения: {e}", exc_info=True)
        return image_bytes


def compress_photos_for_document(
    photos: List[bytes], max_size_pixels: int = 2000 * 2000
) -> List[bytes]:
    """Сжимает список фотографий для вставки в документ."""
    compressed_photos: List[bytes] = []
    for i, photo in enumerate(photos):
        try:
            compressed: bytes = compress_image(
                photo,
                quality=65,
                max_size=2000,
                target_format="JPEG",
            )
            compressed_photos.append(compressed)
            logger.debug(f"Сжато фото {i+1}: {len(photo)} → {len(compressed)} байт")
        except Exception as e:
            logger.warning(f"Ошибка сжатия фото {i+1}: {e}")
            compressed_photos.append(photo)
    return compressed_photos


def calculate_auto_size(
    rows: int,
    cols: int,
    page_width_cm: float = 17.0,
    page_height_cm: float = 25.0,
) -> Tuple[float, float]:
    """Автоматически вычисляет оптимальный размер фото для таблицы."""
    max_cell_width: float = page_width_cm / cols
    max_cell_height: float = page_height_cm / rows

    size_cm: float = min(max_cell_width, max_cell_height) * 0.9
    size_cm = max(2.0, min(size_cm, 10.0))

    return (size_cm, size_cm)


def split_into_pages(photos: List[bytes], rows: int, cols: int) -> List[List[bytes]]:
    """Разбивает список фото на страницы по rows×cols фото на страницу."""
    photos_per_page: int = rows * cols
    if photos_per_page <= 0:
        return [photos]

    pages: List[List[bytes]] = []
    for i in range(0, len(photos), photos_per_page):
        page: List[bytes] = photos[i : i + photos_per_page]
        pages.append(page)

    return pages


def calculate_pages_info(
    photos_count: int, rows: int, cols: int
) -> Dict[str, Union[int, str, float]]:
    """Вычисляет информацию о страницах документа."""
    photos_per_page: int = rows * cols
    total_pages: int = (photos_count + photos_per_page - 1) // photos_per_page
    photos_on_last_page: int = photos_count % photos_per_page

    if photos_on_last_page == 0 and photos_count > 0:
        photos_on_last_page = photos_per_page

    return {
        "total_photos": photos_count,
        "rows": rows,
        "cols": cols,
        "photos_per_page": photos_per_page,
        "total_pages": total_pages,
        "photos_on_last_page": photos_on_last_page,
    }


def get_size_option_name(size_key: str) -> str:
    """Возвращает читаемое название размера."""
    if size_key == "auto":
        return "автоматический"
    elif size_key in SIZE_OPTIONS:
        size_cm: float = SIZE_OPTIONS[size_key][0]
        return f"{size_cm} см"
    return "неизвестный"
