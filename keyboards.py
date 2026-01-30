"""
keyboards.py - Модуль для создания клавиатур бота
"""
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

class Keyboards:
    """Класс для создания всех клавиатур бота"""
    
    @staticmethod
    def create_start_keyboard() -> ReplyKeyboardMarkup:
        """
        Клавиатура для начального состояния (Этап 1: Начало).
        Только начало работы и сервисные кнопки.
        """
        keyboard = [
            ["🟢 Начать"],
            ["📊 Статус", "❓ Помощь"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def create_title_keyboard() -> ReplyKeyboardMarkup:
        """
        Клавиатура для ввода заголовка (Этап 1: Начало).
        Заменяем 'Нет' на 'Без заголовка'.
        """
        keyboard = [
            ["Без заголовка"],
            ["🟢 Начать"],
            ["📊 Статус", "❓ Помощь"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def create_input_keyboard() -> ReplyKeyboardMarkup:
        """
        Клавиатура для ввода данных (Этап 1: Начало).
        Упрощенная версия.
        """
        keyboard = [
            ["🟢 Начать", "◀️ Назад"],
            ["📊 Статус", "❓ Помощь"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def create_upload_keyboard() -> ReplyKeyboardMarkup:
        """
        Клавиатура во время загрузки фото (Этап 2: Загрузка).
        Появляются кнопки 'Готово' и 'Очистить'.
        """
        keyboard = [
            ["✅ Готово", "🧹 Очистить"],
            ["◀️ Назад"],
            ["📊 Статус", "❓ Помощь"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def create_confirmation_keyboard() -> ReplyKeyboardMarkup:
        """
        Клавиатура для подтверждения действий с кнопками Да/Нет.
        Эта клавиатура появляется после загрузки фото.
        """
        keyboard = [
            ["✅ Да, всё верно", "❌ Нет, начать заново"],
            ["🟢 Начать", "◀️ Назад"],
            ["📊 Статус", "❓ Помощь"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def create_size_keyboard() -> InlineKeyboardMarkup:
        """Inline клавиатура для выбора размера фото"""
        keyboard = [
            [InlineKeyboardButton("Маленький (до 3 см)", callback_data='size_small')],
            [InlineKeyboardButton("Средний (до 5 см)", callback_data='size_medium')],
            [InlineKeyboardButton("Большой (до 8 см)", callback_data='size_large')],
            [InlineKeyboardButton("Автоподбор", callback_data='size_auto')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_wait_keyboard() -> ReplyKeyboardMarkup:
        """
        Клавиатура во время обработки (Этап 3: Обработка).
        Только информационные кнопки или минимальный набор.
        """
        keyboard = [
            ["❓ Помощь"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)