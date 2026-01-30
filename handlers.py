"""
handlers.py - Обработчики сообщений и команд бота
"""
import logging
import asyncio
import telegram.error
from datetime import datetime
from typing import Dict, Any
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

from document_creators import (
    get_size_option_name,
    compress_image,
    calculate_pages_info,
    DocumentCreator
)
from config import BotConfig
from keyboards import Keyboards
from document_creators.messages import MessageGenerator  # Импортируем новый MessageGenerator

logger = logging.getLogger(__name__)

# Определяем состояния для ConversationHandler
TITLE, ROWS, COLS, SIZE_OPTION, PHOTOS, CONFIRM, CONFIRM_BACK = range(7)

class BotHandlers:
    """Обработчики команд бота"""
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.user_data: Dict[int, Dict[str, Any]] = {}
        self.messages = MessageGenerator()  # Инициализируем MessageGenerator
        
    def get_button_handler(self):
        """Возвращает обработчик кнопок основной клавиатуры"""
        return MessageHandler(
            filters.TEXT & filters.Regex(
                r'^(🟢 Начать|📊 Статус|❓ Помощь)$'
            ),
            self.button_handler
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопок основной клавиатуры"""
        text = update.message.text
        user_id = update.effective_user.id

        logger.info(f"Пользователь {user_id} нажал кнопку: '{text}'")

        if text == "🟢 Начать":
            return await self.start(update, context)
        elif text == "📊 Статус":
            return await self.status_command(update, context)
        elif text == "❓ Помощь":
            return await self.help_command(update, context)

        # Если кнопка не распознана
        await update.message.reply_text(
            "Неизвестная команда. Пожалуйста, используйте кнопки из меню.",
            reply_markup=Keyboards.create_start_keyboard()
        )
        return None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начало диалога - Этап 1: Начало"""
        user_id = update.effective_user.id
        
        # Очищаем старые данные
        self.cleanup_user_data(user_id)
        
        # Инициализируем новые данные
        self.user_data[user_id] = {
            'title': None,
            'rows': None,
            'cols': None,
            'size_option': None,
            'photos': [],
            'created_at': datetime.now(),
            'state': 'title'  # Добавляем состояние
        }
        
        await update.message.reply_text(
            "🖼️ *Многостраничный Фото-Бот*\n\n"
            "Я создам Word документ из ваших фотографий с невидимыми границами.\n\n"
            "📌 *Новый функционал:*\n"
            "✅ *Многостраничность* - загружайте сколько угодно фото\n"
            "✅ *Автораспределение* - фото автоматически разбиваются на страницы\n"
            "✅ *Гибкие таблицы* - каждая страница отдельная таблица\n\n"
            "📝 Введите заголовок для таблицы (или нажмите 'Без заголовка' если без заголовка):",
            parse_mode='Markdown',
            reply_markup=Keyboards.create_title_keyboard()
        )
        return TITLE
    
    async def handle_no_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка кнопки 'Без заголовка'"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_data:
            await update.message.reply_text(
                "Нет активной сессии. Нажмите '🟢 Начать' для начала работы.",
                reply_markup=Keyboards.create_start_keyboard()
            )
            return ConversationHandler.END
        
        self.user_data[user_id]['title'] = None
        self.user_data[user_id]['state'] = 'rows_input'
        
        await update.message.reply_text(
            "✅ Хорошо, без заголовка.\n\n"
            "Теперь введите количество *СТРОК* в таблице (например, 3):\n\n"
            "*Примечание:* Этот размер будет использоваться для каждой страницы",
            parse_mode='Markdown',
            reply_markup=Keyboards.create_input_keyboard()
        )
        return ROWS
    
    async def get_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получаем название таблицы"""
        user_id = update.effective_user.id
        response = update.message.text.strip().lower()
        
        logger.debug(f"=== DEBUG get_title ===")
        logger.debug(f"Пользователь: {user_id}")
        logger.debug(f"Текст сообщения: '{update.message.text}'")
        logger.debug(f"Обработанный ответ: '{response}'")
        
        if response == 'нет':
            self.user_data[user_id]['title'] = None
            logger.debug(f"Заголовок: None")

            await update.message.reply_text(
                "✅ Хорошо, без заголовка.\n\n"
                "Теперь введите количество *СТРОК* в таблице (например, 3):\n\n"
                "*Примечание:* Этот размер будет использоваться для каждой страницы",
                parse_mode='Markdown',
                reply_markup=Keyboards.create_input_keyboard()
            )
            logger.debug(f"Переход в состояние ROWS")
            self.user_data[user_id]['state'] = 'rows_input'
            return ROWS
        else:
            # Пользователь ввел заголовок
            self.user_data[user_id]['title'] = update.message.text
            logger.debug(f"Заголовок сохранен: '{update.message.text}'")

            await update.message.reply_text(
                f"✅ Заголовок таблицы сохранен: *{update.message.text}*\n\n"
                "Теперь введите количество *СТРОК* в таблице (например, 3):\n\n"
                "*Примечание:* Этот размер будет использоваться для каждой странице",
                parse_mode='Markdown',
                reply_markup=Keyboards.create_input_keyboard()
            )
            logger.debug(f"Переход в состояние ROWS")
            self.user_data[user_id]['state'] = 'rows_input'
            return ROWS
    
    async def get_rows(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получаем количество строк"""
        user_id = update.effective_user.id
        
        try:
            rows = int(update.message.text)
            if rows <= 0:
                raise ValueError("Количество должно быть положительным")
            if rows > self.config.max_rows:
                await update.message.reply_text(
                    f"⚠️ Для стабильной работы рекомендуется не более {self.config.max_rows} строк.",
                    reply_markup=Keyboards.create_input_keyboard()
                )
            
            self.user_data[user_id]['rows'] = rows
            self.user_data[user_id]['state'] = 'cols_input'
            
            await update.message.reply_text(
                f"✅ Строк на странице: *{rows}*\n\n"
                "Теперь введите количество *СТОЛБЦОВ* в таблице (например, 4):\n\n"
                "*Примечание:* Этот размер будет использоваться для каждой страницы",
                parse_mode='Markdown',
                reply_markup=Keyboards.create_input_keyboard()
            )
            return COLS
        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, введите целое положительное число (например, 3):",
                reply_markup=Keyboards.create_input_keyboard()
            )
            return ROWS
    
    async def get_cols(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получаем количество столбцов"""
        user_id = update.effective_user.id
        
        try:
            cols = int(update.message.text)
            if cols <= 0:
                raise ValueError("Количество должно быть положительным")
            if cols > self.config.max_cols:
                await update.message.reply_text(
                    f"⚠️ Для лучшего качества рекомендуется не более {self.config.max_cols} столбцов.",
                    reply_markup=Keyboards.create_input_keyboard()
                )
            
            rows = self.user_data[user_id]['rows']
            photos_per_page = rows * cols
            
            if photos_per_page > self.config.max_photos:
                await update.message.reply_text(
                    f"❌ Слишком много фото на странице ({photos_per_page}). "
                    f"Максимально разрешено: {self.config.max_photos}",
                    parse_mode='Markdown',
                    reply_markup=Keyboards.create_input_keyboard()
                )
                return COLS
            
            self.user_data[user_id]['cols'] = cols
            self.user_data[user_id]['state'] = 'size_selection'
            
            # Используем MessageGenerator для сообщения о выборе размера
            await update.message.reply_text(
                self.messages.get_size_selection_message(rows, cols),
                parse_mode='Markdown',
                reply_markup=Keyboards.create_size_keyboard()  # Inline клавиатура
            )
            return SIZE_OPTION
        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, введите целое положительное число (например, 4):",
                reply_markup=Keyboards.create_input_keyboard()
            )
            return COLS
    
    async def size_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка выбора размера фото - переход к Этапу 2: Загрузка"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        size_key = query.data.replace('size_', '')
        
        self.user_data[user_id]['size_option'] = size_key
        self.user_data[user_id]['state'] = 'upload_photos'
        
        size_text = get_size_option_name(size_key)
        rows = self.user_data[user_id]['rows']
        cols = self.user_data[user_id]['cols']
        
        # Используем MessageGenerator для инструкций по загрузке
        await query.edit_message_text(
            self.messages.get_upload_instructions(rows, cols, size_text),
            parse_mode='Markdown'
        )
        
        # После выбора размера переключаем на клавиатуру для загрузки
        await context.bot.send_message(
            chat_id=user_id,
            text="Теперь вы можете загружать фото:",
            reply_markup=Keyboards.create_upload_keyboard()
        )
        
        return PHOTOS
    
    async def get_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получаем фотографии от пользователя"""
        user_id = update.effective_user.id
        
        logger.info(f"=== ПОЛУЧЕНО СООБЩЕНИЕ от пользователя {user_id} ===")
        
        if user_id not in self.user_data:
            logger.warning(f"Пользователь {user_id} не найден в данных")
            await update.message.reply_text(
                "Сессия устарела. Нажмите '🟢 Начать' для начала.",
                reply_markup=Keyboards.create_start_keyboard()
            )
            return ConversationHandler.END
        
        try:
            photo_bytes = None

            # Проверяем, есть ли фото в сообщении
            if update.message.photo:
                logger.info(f"Получено как фото, размеров: {len(update.message.photo)}")
                photo_file = await update.message.photo[-1].get_file()
                photo_bytes = await photo_file.download_as_bytearray()

            elif update.message.document:
                logger.info(f"Получено как документ: {update.message.document.file_name}")
                # Проверяем, что это изображение
                mime_type = update.message.document.mime_type
                if mime_type and ('image' in mime_type):
                    photo_file = await update.message.document.get_file()
                    photo_bytes = await photo_file.download_as_bytearray()
                else:
                    logger.warning(f"Документ не является изображением: {mime_type}")
                    await update.message.reply_text(
                        "Пожалуйста, отправьте фото в формате JPG или PNG",
                        reply_markup=Keyboards.create_upload_keyboard()
                    )
                    return PHOTOS

            if not photo_bytes:
                logger.warning(f"Не удалось получить фото из сообщения")
                await update.message.reply_text(
                    "Пожалуйста, отправьте фото в формате JPG или PNG",
                    reply_markup=Keyboards.create_upload_keyboard()
                )
                return PHOTOS

            logger.info(f"Фото загружено, размер в байтах: {len(photo_bytes)}")

            # Сжимаем фото
            logger.info(f"Сжимаем фото...")
            compressed_bytes = compress_image(
                photo_bytes, 
                self.config.image_quality, 
                self.config.image_max_size
            )
            logger.info(f"Фото сжато, размер после сжатия: {len(compressed_bytes)}")

            # Сохраняем сжатое фото
            self.user_data[user_id]['photos'].append(compressed_bytes)
            logger.info(f"Фото сохранено. Всего фото: {len(self.user_data[user_id]['photos'])}")

            rows = self.user_data[user_id]['rows']
            cols = self.user_data[user_id]['cols']
            received = len(self.user_data[user_id]['photos'])
            
            # Используем MessageGenerator для прогресса загрузки
            response_text = self.messages.generate_upload_progress(
                current=received,
                rows=rows,
                cols=cols
            )

            logger.info(f"Отправляем ответ пользователю")
            await update.message.reply_text(
                response_text, 
                parse_mode='Markdown',
                reply_markup=Keyboards.create_upload_keyboard()
            )

            return PHOTOS
        except Exception as e:
            logger.error(f"Ошибка при обработке фото: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Ошибка при обработке фото. Попробуйте отправить фото снова.",
                reply_markup=Keyboards.create_upload_keyboard()
            )
            return PHOTOS
    
    async def back_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопки Назад"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_data:
            await update.message.reply_text(
                "Нет активной сессии. Нажмите '🟢 Начать' для начала работы.",
                reply_markup=Keyboards.create_start_keyboard()
            )
            return ConversationHandler.END
        
        # Определяем текущий шаг на основе состояния
        state = self.user_data[user_id].get('state', 'start')
        
        if state == 'upload_photos' and self.user_data[user_id].get('photos'):
            # Если есть фото, спрашиваем подтверждение
            await update.message.reply_text(
                "⚠️ *Внимание!*\n\n"
                "У вас есть загруженные фотографии. Возврат приведет к их удалению.\n\n"
                "Вы уверены, что хотите вернуться назад?",
                parse_mode='Markdown',
                reply_markup=Keyboards.create_confirmation_keyboard()
            )
            return CONFIRM_BACK
            
        elif state == 'upload_photos':
            # Возвращаем к выбору размера
            rows = self.user_data[user_id]['rows']
            cols = self.user_data[user_id]['cols']
            photos_per_page = rows * cols
            
            await update.message.reply_text(
                f"Возвращаю к выбору размера.\n\n"
                f"✅ Размер таблицы: *{rows}×{cols}*\n"
                f"📍 Фото на странице: *{photos_per_page}*\n\n"
                "📏 Выберите размер фотографий в таблице:",
                parse_mode='Markdown',
                reply_markup=Keyboards.create_size_keyboard()
            )
            self.user_data[user_id]['state'] = 'size_selection'
            return SIZE_OPTION
            
        elif state == 'size_selection':
            # Возвращаем к вводу столбцов
            rows = self.user_data[user_id]['rows']
            await update.message.reply_text(
                f"Возвращаю к настройке таблиции.\n\n"
                f"✅ Строк на странице: *{rows}*\n\n"
                "Теперь введите количество *СТОЛБЦОВ* в таблице (например, 4):\n\n"
                "*Примечание:* Этот размер будет использоваться для каждой страницы",
                parse_mode='Markdown',
                reply_markup=Keyboards.create_input_keyboard()
            )
            self.user_data[user_id]['state'] = 'cols_input'
            return COLS
            
        elif state == 'cols_input':
            # Возвращаем к вводу строк
            await update.message.reply_text(
                "Возвращаю к началу настройки таблицы.\n\n"
                "Введите количество *СТРОК* в таблице (например, 3):\n\n"
                "*Примечание:* Этот размер будет использоваться для каждой страницы",
                parse_mode='Markdown',
                reply_markup=Keyboards.create_input_keyboard()
            )
            self.user_data[user_id]['state'] = 'rows_input'
            return ROWS
            
        else:
            # Возвращаем к началу
            await update.message.reply_text(
                "Начинаем заново.\n\n"
                "📝 Введите заголовок для таблицы (или нажмите 'Без заголовка' если без заголовка):",
                parse_mode='Markdown',
                reply_markup=Keyboards.create_title_keyboard()
            )
            self.user_data[user_id]['state'] = 'title'
            return TITLE
    
    async def handle_confirm_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения возврата"""
        text = update.message.text.lower()
        
        if text in ['да', 'yes', 'ок', 'окей', 'вернуться']:
            user_id = update.effective_user.id
            if user_id in self.user_data:
                # Очищаем фото и возвращаем к предыдущему шагу
                self.user_data[user_id]['photos'] = []
                
                if self.user_data[user_id].get('size_option'):
                    rows = self.user_data[user_id]['rows']
                    cols = self.user_data[user_id]['cols']
                    photos_per_page = rows * cols
                    
                    await update.message.reply_text(
                        f"✅ Фотографии удалены.\n\n"
                        f"📍 Фото на странице: *{photos_per_page}*\n\n"
                        "📏 Выберите размер фотографий в таблице:",
                        parse_mode='Markdown',
                        reply_markup=Keyboards.create_size_keyboard()
                    )
                    self.user_data[user_id]['state'] = 'size_selection'
                    return SIZE_OPTION
                else:
                    await update.message.reply_text(
                        "Начинаем заново.\n\n"
                        "📝 Введите заголовок для таблицы (или нажмите 'Без заголовка' если без заголовка):",
                        parse_mode='Markdown',
                        reply_markup=Keyboards.create_title_keyboard()
                    )
                    self.user_data[user_id]['state'] = 'title'
                    return TITLE
        else:
            await update.message.reply_text(
                "Возврат отменен. Продолжаем работу с текущими фотографиями.\n\n"
                "Вы можете загрузить еще фото или нажать '✅ Готово'.",
                reply_markup=Keyboards.create_upload_keyboard()
            )
            self.user_data[user_id]['state'] = 'upload_photos'
            return PHOTOS
    
    async def done_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Завершение загрузки фото"""
        user_id = update.effective_user.id
        
        logger.info(f"=== ВЫЗВАНА КОМАНДА /done от пользователя {user_id} ===")
        logger.info(f"Пользователь в данных: {user_id in self.user_data}")
        
        if user_id not in self.user_data:
            logger.warning(f"Пользователь {user_id} не найден в данных")
            await update.message.reply_text(
                "Сессия устарела. Нажмите '🟢 Начать' для начала.",
                reply_markup=Keyboards.create_start_keyboard()
            )
            return ConversationHandler.END
        
        photos_count = len(self.user_data[user_id]['photos'])
        logger.info(f"Количество загруженных фото: {photos_count}")
        
        if photos_count == 0:
            await update.message.reply_text(
                "❌ Вы не загрузили ни одной фотографии.\n"
                "Отправьте фото или нажмите '🟢 Начать' для начала.",
                reply_markup=Keyboards.create_upload_keyboard()
            )
            return PHOTOS
        
        rows = self.user_data[user_id]['rows']
        cols = self.user_data[user_id]['cols']
        page_info = calculate_pages_info(photos_count, rows, cols)
        
        # Используем MessageGenerator для сообщения подтверждения
        confirmation_text = self.messages.get_confirmation_message(
            title=self.user_data[user_id]['title'],
            photos_count=photos_count,
            rows=rows,
            cols=cols,
            size_option=self.user_data[user_id]['size_option'],
            page_info=page_info
        )
        
        logger.info(f"Отправляем подтверждение пользователю с клавиатурой")
        await update.message.reply_text(
            confirmation_text,
            parse_mode='Markdown',
            reply_markup=Keyboards.create_confirmation_keyboard()  # Клавиатура с Да/Нет
        )
        
        logger.info(f"Переход в состояние CONFIRM")
        self.user_data[user_id]['state'] = 'confirmation'
        return CONFIRM
    
    async def handle_confirm_yes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопки 'Да, всё верно'"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_data:
            await update.message.reply_text(
                "Сессия устарела. Нажмите '🟢 Начать' для начала.",
                reply_markup=Keyboards.create_start_keyboard()
            )
            return ConversationHandler.END
        
        # Создаем документ
        await self.create_document_from_text(update, context, user_id)
        return ConversationHandler.END
    
    async def handle_confirm_no(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопки 'Нет, начать заново'"""
        user_id = update.effective_user.id
        
        await update.message.reply_text(
            "Операция отменена. Для начала нового документа нажмите '🟢 Начать'",
            reply_markup=Keyboards.create_start_keyboard()
        )
        self.cleanup_user_data(user_id)
        return ConversationHandler.END
    
    async def create_document_from_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Создает документ из текстового подтверждения"""
        await self._create_and_send_document(context, user_id)
    
    async def _create_and_send_document(self, context, user_id):
        """Общая логика создания и отправки документа с явным прогрессом"""
        try:
            logger.info(f"=== НАЧАЛО СОЗДАНИЯ ДОКУМЕНТА для пользователя {user_id} ===")
        
            if user_id not in self.user_data:
                logger.warning(f"Пользователь {user_id} не найден в данных")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=self.messages.get_session_expired_error(),
                    parse_mode='Markdown'
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text=self.messages.get_start_prompt(),
                    reply_markup=Keyboards.create_start_keyboard()
                )
                return
        
            photos_count = len(self.user_data[user_id]['photos'])
            rows = self.user_data[user_id]['rows']
            cols = self.user_data[user_id]['cols']
            page_info = calculate_pages_info(photos_count, rows, cols)
        
            logger.info(f"Параметры документа: {photos_count} фото, таблица {rows}×{cols}, "
                       f"{page_info['total_pages']} страниц")
        
            # Проверяем ограничение на количество фото
            if photos_count > BotConfig.max_photos:
                logger.warning(f"Слишком много фото: {photos_count} > {BotConfig.max_photos}")
                error_text = self.messages.get_too_many_photos_error(photos_count, BotConfig.max_photos)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=error_text,
                    parse_mode='Markdown'
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text=self.messages.get_start_prompt(),
                    reply_markup=Keyboards.create_start_keyboard()
                )
                return
        
            # 1. 🛠️ Создаю документ... (10%)
            creating_text = self.messages.get_creating_document_message_with_progress(
                photos_count, rows, cols, page_info, progress=10
            )
            creating_message = await context.bot.send_message(
                chat_id=user_id,
                text=creating_text,
                parse_mode='Markdown',
                reply_markup=Keyboards.create_wait_keyboard()
            )
        
            # Отправляем действие "загрузка документа"
            await context.bot.send_chat_action(
                chat_id=user_id,
                action=ChatAction.UPLOAD_DOCUMENT
            )
        
            # Создаем документ
            logger.info("Создаю DocumentCreator...")
            creator = DocumentCreator(
                title=self.user_data[user_id]['title'],
                rows=rows,
                cols=cols,
                size_option=self.user_data[user_id]['size_option']
            )
        
            # Создаем многостраничный документ
            logger.info(f"Начинаю создание документа из {photos_count} фото...")
            document_bytes = creator.create_multi_page_document(self.user_data[user_id]['photos'])
        
            doc_size_mb = len(document_bytes) / 1024 / 1024
            logger.info(f"Документ создан: {doc_size_mb:.2f} MB")
        
            # Проверяем размер документа
            if doc_size_mb > 45:
                logger.error(f"Документ слишком большой: {doc_size_mb:.2f} MB")
                error_text = self.messages.get_document_too_big_error(doc_size_mb)
                
                # Отправляем новое сообщение об ошибке вместо редактирования
                await context.bot.send_message(
                    chat_id=user_id,
                    text=error_text,
                    parse_mode='Markdown',
                    reply_markup=Keyboards.create_start_keyboard()
                )
                
                # Очищаем данные
                self.cleanup_user_data(user_id)
                return
        
            # 2. 📤 Отправляю документ... (50%)
            sending_text = self.messages.get_sending_document_message_with_progress(
                doc_size_mb, progress=50
            )
            
            # Отправляем новое сообщение вместо редактирования
            sending_message = await context.bot.send_message(
                chat_id=user_id,
                text=sending_text,
                parse_mode='Markdown',
                reply_markup=Keyboards.create_wait_keyboard()
            )
        
            # Создаем подпись для файла (короткая версия)
            file_caption = self.messages.get_document_caption(
                title=self.user_data[user_id]['title'],
                photos_count=photos_count,
                rows=rows,
                cols=cols,
                size_option=self.user_data[user_id]['size_option'],
                page_info=page_info
            )
            
            filename = self.messages.generate_filename(
                title=self.user_data[user_id]['title'],
                photos_count=photos_count,
                rows=rows,
                cols=cols
            )
        
            # Очищаем данные пользователя (чтобы освободить память) перед отправкой
            self.cleanup_user_data(user_id)
        
            try:
                # Отправляем документ с короткой подписью
                sent_document = await context.bot.send_document(
                    chat_id=user_id,
                    document=document_bytes,
                    filename=filename,
                    caption=file_caption,
                    parse_mode='Markdown',
                    read_timeout=300,
                    write_timeout=300,
                    connect_timeout=120,
                )
                logger.info("✅ Документ успешно отправлен!")
        
                # 3. 📎 Файл отправлен (80%)
                file_sent_text = self.messages.get_file_sent_message(progress=80)
                file_sent_message = await context.bot.send_message(
                    chat_id=user_id,
                    text=file_sent_text,
                    parse_mode='Markdown',
                    reply_markup=Keyboards.create_wait_keyboard()
                )
                
                # Небольшая задержка для визуального эффекта прогресса
                await asyncio.sleep(1)
        
                # 4. ✅ Документ успешно отправлен! (100%)
                success_text = self.messages.get_document_success_message_with_progress(
                    photos_count, rows, cols, page_info, doc_size_mb, progress=100
                )
                success_message = await context.bot.send_message(
                    chat_id=user_id,
                    text=success_text,
                    parse_mode='Markdown',
                    reply_markup=Keyboards.create_start_keyboard()
                )
        
            except telegram.error.TimedOut:
                logger.error("Таймаут при отправке документа в Telegram")
                error_text = self.messages.get_timeout_error(doc_size_mb)
                await context.bot.send_message(
                    chat_id=user_id,
                    text=error_text,
                    parse_mode='Markdown',
                    reply_markup=Keyboards.create_start_keyboard()
                )
        
            except telegram.error.BadRequest as e:
                logger.error(f"Ошибка BadRequest при отправке: {e}")
                if "file is too big" in str(e).lower():
                    error_text = self.messages.get_file_too_big_error(doc_size_mb)
                else:
                    error_text = self.messages.get_generic_api_error(str(e))
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=error_text,
                    parse_mode='Markdown',
                    reply_markup=Keyboards.create_start_keyboard()
                )
        
        except telegram.error.TimedOut:
            logger.error("Таймаут при создании/отправке документа")
            error_text = self.messages.get_creation_timeout_error()
            await context.bot.send_message(
                chat_id=user_id,
                text=error_text,
                parse_mode='Markdown',
                reply_markup=Keyboards.create_start_keyboard()
            )
            self.cleanup_user_data(user_id)
        
        except Exception as e:
            logger.error(f"Ошибка при создании документа: {e}", exc_info=True)
            error_text = self.messages.get_generic_creation_error(str(e))
            await context.bot.send_message(
                chat_id=user_id,
                text=error_text,
                parse_mode='Markdown',
                reply_markup=Keyboards.create_start_keyboard()
            )
            self.cleanup_user_data(user_id)
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отмена диалога"""
        user_id = update.effective_user.id
        self.cleanup_user_data(user_id)
        
        await update.message.reply_text(
            "Операция отменена. Данные удалены.\n"
            "Для начала новой работы нажмите '🟢 Начать'",
            reply_markup=Keyboards.create_start_keyboard()
        )
        return ConversationHandler.END
    
    async def cleanup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ручная очистка данных пользователя"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_data:
            await update.message.reply_text(
                "Нет активной сессии. Нет данных для очистки.",
                reply_markup=Keyboards.create_start_keyboard()
            )
            return
        
        photos_count = len(self.user_data[user_id].get('photos', []))
        self.user_data[user_id]['photos'] = []
        
        await update.message.reply_text(
            f"✅ Очищено {photos_count} фото.\n\n"
            f"Вы можете продолжить загружать фото или нажать '🟢 Начать' для перезапуска.",
            reply_markup=Keyboards.create_upload_keyboard()
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статус бота - адаптивный под текущее состояние"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_data:
            # Общий статус бота
            total_users = len(self.user_data)
            total_photos = sum(len(data.get('photos', [])) for data in self.user_data.values())
            
            await update.message.reply_text(
                f"📊 *Общий статус бота:*\n\n"
                f"• Активных сессий: {total_users}\n"
                f"• Фото в памяти: {total_photos}\n"
                f"• Время: {datetime.now().strftime('%H:%M:%S')}\n\n"
                f"Для начала работы нажмите '🟢 Начать'",
                parse_mode='Markdown',
                reply_markup=Keyboards.create_start_keyboard()
            )
        else:
            # Статус текущей сессии
            user_data = self.user_data[user_id]
            state = user_data.get('state', 'start')
            photos_count = len(user_data.get('photos', []))
            
            status_text = f"📊 *Статус вашей сессии:*\n\n"
            
            if state == 'upload_photos':
                rows = user_data['rows']
                cols = user_data['cols']
                photos_per_page = rows * cols
                total_pages = (photos_count + photos_per_page - 1) // photos_per_page
                
                status_text += (
                    f"• Состояние: *Загрузка фото*\n"
                    f"• Загружено фото: *{photos_count}*\n"
                    f"• Размер таблицы: *{rows}×{cols}*\n"
                    f"• Фото на странице: *{photos_per_page}*\n"
                    f"• Страниц будет: *{total_pages}*\n"
                    f"• Заголовок: {user_data['title'] or 'нет'}\n\n"
                    f"*Действия:*\n"
                    f"• Продолжайте загружать фото\n"
                    f"• Или нажмите '✅ Готово'"
                )
                reply_keyboard = Keyboards.create_upload_keyboard()
                
            elif state == 'size_selection':
                status_text += (
                    f"• Состояние: *Выбор размера фото*\n"
                    f"• Размер таблицы: {user_data['rows']}×{user_data['cols']}\n"
                    f"• Заголовок: {user_data['title'] or 'нет'}\n\n"
                    f"Выберите размер фото из меню выше."
                )
                reply_keyboard = Keyboards.create_input_keyboard()
                
            elif state in ['rows_input', 'cols_input']:
                status_text += (
                    f"• Состояние: *Настройка таблицы*\n"
                    f"• Заголовок: {user_data['title'] or 'нет'}\n\n"
                    f"Следуйте инструкциям для настройки таблицы."
                )
                reply_keyboard = Keyboards.create_input_keyboard()
                
            elif state == 'title':
                status_text += (
                    f"• Состояние: *Ввод заголовка*\n\n"
                    f"Введите заголовок или нажмите 'Без заголовка'."
                )
                reply_keyboard = Keyboards.create_title_keyboard()
                
            else:
                status_text += (
                    f"• Состояние: *Готов к работе*\n\n"
                    f"Для начала нажмите '🟢 Начать'."
                )
                reply_keyboard = Keyboards.create_start_keyboard()
            
            await update.message.reply_text(
                status_text,
                parse_mode='Markdown',
                reply_markup=reply_keyboard
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Справка по боту"""
        user_id = update.effective_user.id
        
        help_text = (
            "🆘 *Помощь по многостраничному боту:*\n\n"
            "*Основные кнопки:*\n"
            "🟢 *Начать* - начать создание документа\n"
            "✅ *Готово* - завершить загрузку фото (появляется на этапе загрузки)\n"
            "◀️ *Назад* - вернуться к предыдущему шагу\n"
            "🧹 *Очистить* - очистить загруженные фото\n"
            "📊 *Статус* - показывает текущий статус\n"
            "❓ *Помощь* - эта справка\n"
            "📝 *Без заголовка* - пропустить ввод заголовка\n"
            "✅ *Да, всё верно* - подтвердить создание документа\n"
            "❌ *Нет, начать заново* - отменить и начать заново\n\n"
            
            "*Процесс работы:*\n"
            "1. Нажмите '🟢 Начать'\n"
            "2. Введите заголовок или нажмите 'Без заголовка'\n"
            "3. Введите количество строк в таблице (например, 3)\n"
            "4. Введите количество столбцов (например, 4)\n"
            "5. Выберите размер фото из меню\n"
            "6. Загружайте фото по одному\n"
            "7. Нажмите '✅ Готово' когда все фото загружены\n"
            "8. Подтвердите создание документа кнопкой '✅ Да, всё верно'\n"
            "9. Получите готовый Word-файл\n\n"
            
            "*Особенности:*\n"
            "• *Многостраничность* - фото автоматически распределяются по страницам\n"
            "• *Гибкие таблицы* - каждая страница содержит отдельную таблицу\n"
            "• *Невидимые границы* - таблица в документе без видимых границ\n"
            "• *Автосжатие* - фото автоматически оптимизируются\n\n"
            
            f"*Ограничения:*\n"
            f"• Максимум строк на странице: {self.config.max_rows}\n"
            f"• Максимум столбцов на странице: {self.config.max_cols}\n"
            f"• Максимум фото на странице: {self.config.max_photos}\n\n"
        )
        
        # Определяем, какую клавиатуру показывать
        if user_id in self.user_data:
            state = self.user_data[user_id].get('state', 'start')
            if state == 'upload_photos':
                reply_keyboard = Keyboards.create_upload_keyboard()
            elif state == 'title':
                reply_keyboard = Keyboards.create_title_keyboard()
            elif state == 'confirmation':
                reply_keyboard = Keyboards.create_confirmation_keyboard()
            else:
                reply_keyboard = Keyboards.create_input_keyboard()
        else:
            reply_keyboard = Keyboards.create_start_keyboard()
        
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=reply_keyboard
        )
    
    def cleanup_user_data(self, user_id: int):
        """Очищает данные пользователя из памяти"""
        if user_id in self.user_data:
            # Очищаем список фотографий
            if 'photos' in self.user_data[user_id]:
                self.user_data[user_id]['photos'] = []
            # Удаляем запись пользователя через некоторое время
            asyncio.create_task(self._delayed_cleanup(user_id))
    
    async def _delayed_cleanup(self, user_id: int, delay: int = 3600):
        """Отложенная очистка данных пользователя"""
        await asyncio.sleep(delay)
        if user_id in self.user_data:
            del self.user_data[user_id]
            logger.info(f"Очищены данные пользователя {user_id}")
    
    async def periodic_cleanup(self, context: ContextTypes.DEFAULT_TYPE):
        """Периодическая очистка старых данных"""
        current_time = datetime.now()
        users_to_clean = []
        
        for user_id, data in self.user_data.items():
            if 'created_at' in data:
                age = (current_time - data['created_at']).total_seconds()
                if age > self.config.session_timeout:
                    users_to_clean.append(user_id)
        
        for user_id in users_to_clean:
            self.cleanup_user_data(user_id)
            logger.info(f"Автоматически очищены данные пользователя {user_id}")
    
    def get_conversation_handler(self) -> ConversationHandler:
        """Возвращает настроенный ConversationHandler"""
        return ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                TITLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_title),
                    MessageHandler(filters.TEXT & filters.Regex(r'^(Без заголовка|◀️ Назад)$'), self.handle_conversation_buttons)
                ],
                ROWS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_rows),
                    MessageHandler(filters.TEXT & filters.Regex(r'^(◀️ Назад|📊 Статус|❓ Помощь)$'), self.handle_conversation_buttons)
                ],
                COLS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_cols),
                    MessageHandler(filters.TEXT & filters.Regex(r'^(◀️ Назад|📊 Статус|❓ Помощь)$'), self.handle_conversation_buttons)
                ],
                SIZE_OPTION: [
                    CallbackQueryHandler(self.size_option, pattern='^size_'),
                    MessageHandler(filters.TEXT & filters.Regex(r'^(◀️ Назад|📊 Статус|❓ Помощь)$'), self.handle_conversation_buttons)
                ],
                PHOTOS: [
                    MessageHandler(filters.PHOTO | filters.Document.IMAGE, self.get_photo),
                    MessageHandler(filters.TEXT & filters.Regex(r'^(✅ Готово|◀️ Назад|🧹 Очистить|📊 Статус|❓ Помощь)$'), self.handle_conversation_buttons)
                ],
                CONFIRM: [
                    MessageHandler(filters.TEXT & filters.Regex(r'^(✅ Да, всё верно|❌ Нет, начать заново|◀️ Назад|📊 Статус|❓ Помощь)$'), self.handle_conversation_buttons)
                ],
                CONFIRM_BACK: [
                    MessageHandler(filters.TEXT, self.handle_confirm_back)
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CommandHandler("start", self.start),
                MessageHandler(filters.TEXT & filters.Regex(r'^(🟢 Начать)$'), self.start)
            ],
            conversation_timeout=7200,
            allow_reentry=True,
        )
    
    async def handle_conversation_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопок внутри ConversationHandler"""
        text = update.message.text
        user_id = update.effective_user.id
        
        logger.info(f"Пользователь {user_id} нажал кнопку в ConversationHandler: '{text}'")
        
        if text == "🟢 Начать":
            return await self.start(update, context)
        elif text == "◀️ Назад":
            return await self.back_command(update, context)
        elif text == "✅ Готово":
            return await self.done_command(update, context)
        elif text == "🧹 Очистить":
            return await self.cleanup_command(update, context)
        elif text == "📊 Статус":
            return await self.status_command(update, context)
        elif text == "❓ Помощь":
            return await self.help_command(update, context)
        elif text == "Без заголовка":
            return await self.handle_no_title(update, context)
        elif text == "✅ Да, всё верно":
            return await self.handle_confirm_yes(update, context)
        elif text == "❌ Нет, начать заново":
            return await self.handle_confirm_no(update, context)
        
        return None

    def get_callback_handlers(self):
        """Возвращает обработчики callback-запросов"""
        return [
            CallbackQueryHandler(self.size_option, pattern='^size_'),
        ]
    
    def get_command_handlers(self):
        """Возвращает список обработчиков команд"""
        return [
            CommandHandler("cleanup", self.cleanup_command),
            CommandHandler("status", self.status_command),
            CommandHandler("help", self.help_command),
        ]