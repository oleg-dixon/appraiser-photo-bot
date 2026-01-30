"""
Базовые функции для создания документов Word.
"""

import io
import logging
from typing import List
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from .constants import SIZE_OPTIONS, A4_WIDTH_CM, A4_HEIGHT_CM, DEFAULT_MARGINS
from .utils import calculate_auto_size

logger = logging.getLogger(__name__)


def set_table_borders(table, visible: bool = False):
    """
    Устанавливает видимость границ таблицы.
    
    Args:
        table: таблица docx
        visible: если True - границы видны, если False - невидимые
    """
    tbl = table._element
    
    # Ищем или создаем элемент границ таблицы
    tblBorders = tbl.find(qn('w:tblBorders'))
    if tblBorders is None:
        tblBorders = OxmlElement('w:tblBorders')
        tblPr = tbl.find(qn('w:tblPr'))
        if tblPr is None:
            tblPr = OxmlElement('w:tblPr')
            tbl.insert(0, tblPr)
        tblPr.insert(0, tblBorders)
    
    if visible:
        border_style = 'single'
        border_size = 4  # 0.5 pt
        border_color = 'C0C0C0'  # светло-серый
    else:
        border_style = 'nil'
        border_size = 0
        border_color = 'auto'
    
    borders = {
        'top': {'val': border_style, 'sz': border_size, 'space': '0', 'color': border_color},
        'left': {'val': border_style, 'sz': border_size, 'space': '0', 'color': border_color},
        'bottom': {'val': border_style, 'sz': border_size, 'space': '0', 'color': border_color},
        'right': {'val': border_style, 'sz': border_size, 'space': '0', 'color': border_color},
        'insideH': {'val': border_style, 'sz': border_size, 'space': '0', 'color': border_color},
        'insideV': {'val': border_style, 'sz': border_size, 'space': '0', 'color': border_color}
    }
    
    for border_name, border_attrs in borders.items():
        border = tblBorders.find(qn(f'w:{border_name}'))
        if border is None:
            border = OxmlElement(f'w:{border_name}')
            tblBorders.append(border)
        
        for key, value in border_attrs.items():
            border.set(qn(f'w:{key}'), str(value))
    
    # Также настраиваем границы для ячеек
    for row in table.rows:
        for cell in row.cells:
            tcBorders = cell._element.find(qn('w:tcBorders'))
            if tcBorders is None:
                tcBorders = OxmlElement('w:tcBorders')
                tcPr = cell._element.find(qn('w:tcPr'))
                if tcPr is None:
                    tcPr = OxmlElement('w:tcPr')
                    cell._element.append(tcPr)
                tcPr.append(tcBorders)
            
            for border_name in ['top', 'left', 'bottom', 'right']:
                border = tcBorders.find(qn(f'w:{border_name}'))
                if border is None:
                    border = OxmlElement(f'w:{border_name}')
                    tcBorders.append(border)
                border.set(qn('w:val'), 'nil')
                border.set(qn('w:sz'), '0')
                border.set(qn('w:space'), '0')
                border.set(qn('w:color'), 'auto')


def create_single_page_document(
    photos: List[bytes], 
    rows: int, 
    cols: int, 
    table_title: str,
    image_size_option: str = 'auto'
) -> Document:
    """
    Создает одностраничный документ с таблицей из фотографий.
    
    Args:
        photos: список фотографий в байтах
        rows: количество строк в таблице
        cols: количество столбцов в таблице
        table_title: заголовок таблицы
        image_size_option: размер изображений ('small', 'medium', 'large', 'auto')
    
    Returns:
        Документ Word
    """
    doc = Document()
    
    # Устанавливаем базовый стиль для всего документа
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    
    # Устанавливаем размер страницы (A4)
    section = doc.sections[0]
    section.page_width = Cm(A4_WIDTH_CM)
    section.page_height = Cm(A4_HEIGHT_CM)
    
    # Устанавливаем поля
    section.left_margin = Cm(DEFAULT_MARGINS['left'])
    section.right_margin = Cm(DEFAULT_MARGINS['right'])
    section.top_margin = Cm(DEFAULT_MARGINS['top'])
    section.bottom_margin = Cm(DEFAULT_MARGINS['bottom'])
    
    # Добавляем заголовок таблицы с жирным шрифтом
    if table_title:
        title_paragraph = doc.add_paragraph()
        title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Явно устанавливаем свойства шрифта
        run = title_paragraph.add_run(table_title)
        run.font.name = 'Times New Roman'
        run.font.bold = True  # ЖИРНЫЙ ТЕКСТ
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(0, 0, 0)  # Черный
        
        # Добавляем отступ после заголовка
        title_paragraph.paragraph_format.space_after = Pt(12)
    
    # Создаем таблицу
    table = doc.add_table(rows=rows, cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    # Убираем автоматические отступы в ячейках
    table.autofit = False
    table.allow_autofit = False
    
    # Рассчитываем размер изображений
    if image_size_option == 'auto':
        # Рассчитываем максимальный размер для заполнения всей страницы
        usable_page_width = A4_WIDTH_CM - (DEFAULT_MARGINS['left'] + DEFAULT_MARGINS['right'])
        usable_page_height = A4_HEIGHT_CM - (DEFAULT_MARGINS['top'] + DEFAULT_MARGINS['bottom'])
        
        cell_width_cm = usable_page_width / cols
        cell_height_cm = usable_page_height / rows
        
        # Берем минимальное значение с небольшим запасом
        image_size_cm = min(cell_width_cm, cell_height_cm) * 0.95
        
        # Ограничиваем разумными пределами
        image_size_cm = max(2.0, min(image_size_cm, 10.0))
        image_width = Cm(image_size_cm)
        # Не задаем height - будет автоматически подбираться для сохранения пропорций
    else:
        # Используем фиксированный размер
        size_cm = SIZE_OPTIONS.get(image_size_option, (5.0, 5.0))
        image_width = Cm(size_cm[0])
        # Не задаем height - будет автоматически подбираться для сохранения пропорций
    
    # Рассчитываем размеры ячеек (немного больше изображений)
    cell_width = image_width + Cm(0.2)
    cell_height = image_width + Cm(0.2)  # Квадратные ячейки для равномерного вида
    
    # Заполняем таблицу фотографиями
    for row_idx in range(rows):
        for col_idx in range(cols):
            photo_index = row_idx * cols + col_idx
            if photo_index < len(photos):
                cell = table.cell(row_idx, col_idx)
                
                # Убираем отступы в ячейке
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                
                # Убираем внутренние отступы
                tcPr = cell._element.tcPr
                if tcPr is None:
                    tcPr = OxmlElement('w:tcPr')
                    cell._element.append(tcPr)
                
                # Устанавливаем нулевые отступы
                tcMar = OxmlElement('w:tcMar')
                for pos in ['top', 'left', 'bottom', 'right']:
                    mar = OxmlElement(f'w:{pos}')
                    mar.set(qn('w:w'), '0')
                    mar.set(qn('w:type'), 'dxa')
                    tcMar.append(mar)
                tcPr.append(tcMar)
                
                # Добавляем изображение
                if photos[photo_index]:
                    paragraph = cell.paragraphs[0]
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    paragraph.paragraph_format.space_before = Pt(0)
                    paragraph.paragraph_format.space_after = Pt(0)
                    paragraph.paragraph_format.line_spacing = 1.0
                    
                    run = paragraph.add_run()
                    
                    image_stream = io.BytesIO(photos[photo_index])
                    try:
                        # ТОЛЬКО ШИРИНА - сохраняет пропорции изображения
                        # Высота подбирается автоматически
                        run.add_picture(image_stream, width=image_width)
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении изображения: {e}")
                        run.add_text("[Изображение]")
            else:
                # Пустая ячейка
                cell = table.cell(row_idx, col_idx)
                cell.text = ""
    
    # Настраиваем ширину столбцов и высоту строк
    for row in table.rows:
        row.height_rule = 1  # Точно заданная высота
        row.height = cell_height
        
        for cell in row.cells:
            cell.width = cell_width
    
    # Устанавливаем одинаковую ширину для всех столбцов
    for col_idx in range(cols):
        for row_idx in range(rows):
            try:
                cell = table.cell(row_idx, col_idx)
                cell.width = cell_width
            except:
                pass
    
    # Убираем границы таблицы
    set_table_borders(table, visible=False)
    
    return doc


# Алиас для обратной совместимости
create_document_with_table = create_single_page_document