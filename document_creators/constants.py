"""
Константы для создания документов.
"""

from PIL import ImageFile

# Разрешить загрузку усеченных изображений
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Опции для размера изображений
SIZE_OPTIONS = {
    'small': (3.0, 3.0),   # см
    'medium': (5.0, 5.0),  # см
    'large': (8.0, 8.0),   # см
    'auto': None  # автоматический подбор
}

# Размеры страницы A4
A4_WIDTH_CM = 21.0
A4_HEIGHT_CM = 29.7

# Поля по умолчанию
DEFAULT_MARGINS = {
    'left': 1.0,      # см
    'right': 1.0,     # см
    'top': 0.5,       # см (минимальный)
    'bottom': 1.0,    # см
}

# Максимальные размеры
MAX_IMAGE_SIZE = 1200  # пикселей
DEFAULT_IMAGE_QUALITY = 70