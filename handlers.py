"""Обработчики сообщений и команд бота."""

import logging
import asyncio
import telegram.error
from datetime import datetime
from typing import Dict, Any, List, Optional
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
from document_creators.messages import MessageGenerator

logger = logging.getLogger(__name__)

TITLE, ROWS, COLS, SIZE_OPTION, PHOTOS, CONFIRM, CONFIRM_BACK = range(7)


class BotHandlers:
    """Обработчики команд бота."""

    def __init__(self, config: BotConfig) -> None:
        self.config: BotConfig = config
        self.user_data: Dict[int, Dict[str, Any]] = {}
        self.messages: MessageGenerator = MessageGenerator()

    def get_button_handler(self) -> MessageHandler:
        """Возвращает обработчик кнопок основной клавиатуры."""
        return MessageHandler(
            filters.TEXT & filters.Regex(r"^(🟢 Начать|📊 Статус|❓ Помощь)$"),
            self.button_handler,
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
        """Обработчик кнопок основной клавиатуры."""
        text: str = update.message.text
        user_id: int = update.effective_user.id

        logger.info(f"Пользователь {user_id} нажал кнопку: '{text}'")

        if text == "🟢 Начать":
            return await self.start(update, context)
        elif text == "📊 Статус":
            return await self.status_command(update, context)
        elif text == "❓ Помощь":
            return await self.help_command(update, context)

        await update.message.reply_text(
            self.messages.get_unknown_button_message(),
            reply_markup=Keyboards.create_start_keyboard(),
        )
        return None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начало диалога - Этап 1: Начало."""
        user_id: int = update.effective_user.id

        self.cleanup_user_data(user_id)

        self.user_data[user_id] = {
            "title": None,
            "rows": None,
            "cols": None,
            "size_option": None,
            "photos": [],
            "created_at": datetime.now(),
            "state": "title",
        }

        await update.message.reply_text(
            self.messages.get_initial_bot_message(),
            parse_mode="Markdown",
            reply_markup=Keyboards.create_title_keyboard(),
        )
        return TITLE

    async def handle_no_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка кнопки 'Без заголовка'."""
        user_id: int = update.effective_user.id

        if user_id not in self.user_data:
            await update.message.reply_text(
                self.messages.get_no_active_session_message(),
                reply_markup=Keyboards.create_start_keyboard(),
            )
            return ConversationHandler.END

        self.user_data[user_id]["title"] = None
        self.user_data[user_id]["state"] = "rows_input"

        await update.message.reply_text(
            self.messages.get_no_title_message(),
            parse_mode="Markdown",
            reply_markup=Keyboards.create_input_keyboard(),
        )
        return ROWS

    async def get_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получаем название таблицы."""
        user_id: int = update.effective_user.id
        response: str = update.message.text.strip().lower()

        logger.debug(f"=== DEBUG get_title ===")
        logger.debug(f"Пользователь: {user_id}")
        logger.debug(f"Текст сообщения: '{update.message.text}'")
        logger.debug(f"Обработанный ответ: '{response}'")

        if response == "нет":
            self.user_data[user_id]["title"] = None
            logger.debug("Заголовок: None")

            await update.message.reply_text(
                self.messages.get_no_title_message(),
                parse_mode="Markdown",
                reply_markup=Keyboards.create_input_keyboard(),
            )
            logger.debug("Переход в состояние ROWS")
            self.user_data[user_id]["state"] = "rows_input"
            return ROWS
        else:
            self.user_data[user_id]["title"] = update.message.text
            logger.debug(f"Заголовок сохранен: '{update.message.text}'")

            await update.message.reply_text(
                self.messages.get_title_saved_message(update.message.text),
                parse_mode="Markdown",
                reply_markup=Keyboards.create_input_keyboard(),
            )
            logger.debug("Переход в состояние ROWS")
            self.user_data[user_id]["state"] = "rows_input"
            return ROWS

    async def get_rows(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получаем количество строк."""
        user_id: int = update.effective_user.id

        try:
            rows: int = int(update.message.text)
            if rows <= 0:
                raise ValueError("Количество должно быть положительным")
            if rows > self.config.max_rows:
                await update.message.reply_text(
                    self.messages.get_validation_rows_message(self.config.max_rows),
                    reply_markup=Keyboards.create_input_keyboard(),
                )

            self.user_data[user_id]["rows"] = rows
            self.user_data[user_id]["state"] = "cols_input"

            await update.message.reply_text(
                self.messages.get_rows_saved_message(rows),
                parse_mode="Markdown",
                reply_markup=Keyboards.create_input_keyboard(),
            )
            return COLS
        except ValueError:
            await update.message.reply_text(
                self.messages.get_validation_positive_integer_message(),
                reply_markup=Keyboards.create_input_keyboard(),
            )
            return ROWS

    async def get_cols(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получаем количество столбцов."""
        user_id: int = update.effective_user.id

        try:
            cols: int = int(update.message.text)
            if cols <= 0:
                raise ValueError("Количество должно быть положительным")
            if cols > self.config.max_cols:
                await update.message.reply_text(
                    self.messages.get_validation_columns_message(self.config.max_cols),
                    reply_markup=Keyboards.create_input_keyboard(),
                )

            rows: int = self.user_data[user_id]["rows"]
            photos_per_page: int = rows * cols

            if photos_per_page > self.config.max_photos:
                await update.message.reply_text(
                    self.messages.get_too_many_photos_per_page_message(
                        photos_per_page, self.config.max_photos
                    ),
                    parse_mode="Markdown",
                    reply_markup=Keyboards.create_input_keyboard(),
                )
                return COLS

            self.user_data[user_id]["cols"] = cols
            self.user_data[user_id]["state"] = "size_selection"

            await update.message.reply_text(
                self.messages.get_size_selection_message(rows, cols),
                parse_mode="Markdown",
                reply_markup=Keyboards.create_size_keyboard(),
            )
            return SIZE_OPTION
        except ValueError:
            await update.message.reply_text(
                self.messages.get_validation_positive_integer_message(),
                reply_markup=Keyboards.create_input_keyboard(),
            )
            return COLS

    async def size_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка выбора размера фото - переход к Этапу 2: Загрузка."""
        query = update.callback_query
        await query.answer()

        user_id: int = update.effective_user.id
        size_key: str = query.data.replace("size_", "")

        self.user_data[user_id]["size_option"] = size_key
        self.user_data[user_id]["state"] = "upload_photos"

        size_text: str = get_size_option_name(size_key)
        rows: int = self.user_data[user_id]["rows"]
        cols: int = self.user_data[user_id]["cols"]

        await query.edit_message_text(
            self.messages.get_upload_instructions(rows, cols, size_text),
            parse_mode="Markdown",
        )

        await context.bot.send_message(
            chat_id=user_id,
            text="Теперь вы можете загружать фото:",
            reply_markup=Keyboards.create_upload_keyboard(),
        )

        return PHOTOS

    async def get_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получаем фотографии от пользователя."""
        user_id: int = update.effective_user.id

        logger.info(f"=== ПОЛУЧЕНО СООБЩЕНИЕ от пользователя {user_id} ===")

        if user_id not in self.user_data:
            logger.warning(f"Пользователь {user_id} не найден в данных")
            await update.message.reply_text(
                self.messages.get_session_expired_message(),
                reply_markup=Keyboards.create_start_keyboard(),
            )
            return ConversationHandler.END

        try:
            photo_bytes = None

            if update.message.photo:
                logger.info(f"Получено как фото, размеров: {len(update.message.photo)}")
                photo_file = await update.message.photo[-1].get_file()
                photo_bytes = await photo_file.download_as_bytearray()

            elif update.message.document:
                logger.info(f"Получено как документ: {update.message.document.file_name}")
                mime_type = update.message.document.mime_type
                if mime_type and ("image" in mime_type):
                    photo_file = await update.message.document.get_file()
                    photo_bytes = await photo_file.download_as_bytearray()
                else:
                    logger.warning(f"Документ не является изображением: {mime_type}")
                    await update.message.reply_text(
                        self.messages.get_photo_format_error(),
                        reply_markup=Keyboards.create_upload_keyboard(),
                    )
                    return PHOTOS

            if not photo_bytes:
                logger.warning("Не удалось получить фото из сообщения")
                await update.message.reply_text(
                    self.messages.get_photo_format_error(),
                    reply_markup=Keyboards.create_upload_keyboard(),
                )
                return PHOTOS

            logger.info(f"Фото загружено, размер в байтах: {len(photo_bytes)}")

            logger.info("Сжимаем фото...")
            compressed_bytes: bytes = compress_image(
                photo_bytes, self.config.image_quality, self.config.image_max_size
            )
            logger.info(f"Фото сжато, размер после сжатия: {len(compressed_bytes)}")

            self.user_data[user_id]["photos"].append(compressed_bytes)
            logger.info(f"Фото сохранено. Всего фото: {len(self.user_data[user_id]['photos'])}")

            rows: int = self.user_data[user_id]["rows"]
            cols: int = self.user_data[user_id]["cols"]
            received: int = len(self.user_data[user_id]["photos"])

            response_text: str = self.messages.generate_upload_progress(
                current=received, rows=rows, cols=cols
            )

            logger.info("Отправляем ответ пользователю")
            await update.message.reply_text(
                response_text,
                parse_mode="Markdown",
                reply_markup=Keyboards.create_upload_keyboard(),
            )

            return PHOTOS
        except Exception as e:
            logger.error(f"Ошибка при обработке фото: {e}", exc_info=True)
            await update.message.reply_text(
                self.messages.get_photo_processing_error(),
                reply_markup=Keyboards.create_upload_keyboard(),
            )
            return PHOTOS

    async def back_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка кнопки Назад."""
        user_id: int = update.effective_user.id

        if user_id not in self.user_data:
            await update.message.reply_text(
                self.messages.get_no_active_session_message(),
                reply_markup=Keyboards.create_start_keyboard(),
            )
            return ConversationHandler.END

        state: str = self.user_data[user_id].get("state", "start")

        if state == "upload_photos" and self.user_data[user_id].get("photos"):
            await update.message.reply_text(
                self.messages.get_back_confirmation_message(),
                parse_mode="Markdown",
                reply_markup=Keyboards.create_confirmation_keyboard(),
            )
            return CONFIRM_BACK

        elif state == "upload_photos":
            rows: int = self.user_data[user_id]["rows"]
            cols: int = self.user_data[user_id]["cols"]

            await update.message.reply_text(
                self.messages.get_back_to_size_message(rows, cols),
                parse_mode="Markdown",
                reply_markup=Keyboards.create_size_keyboard(),
            )
            self.user_data[user_id]["state"] = "size_selection"
            return SIZE_OPTION

        elif state == "size_selection":
            rows: int = self.user_data[user_id]["rows"]
            await update.message.reply_text(
                self.messages.get_back_to_columns_message(rows),
                parse_mode="Markdown",
                reply_markup=Keyboards.create_input_keyboard(),
            )
            self.user_data[user_id]["state"] = "cols_input"
            return COLS

        elif state == "cols_input":
            await update.message.reply_text(
                self.messages.get_back_to_rows_message(),
                parse_mode="Markdown",
                reply_markup=Keyboards.create_input_keyboard(),
            )
            self.user_data[user_id]["state"] = "rows_input"
            return ROWS

        else:
            await update.message.reply_text(
                self.messages.get_back_to_title_message(),
                parse_mode="Markdown",
                reply_markup=Keyboards.create_title_keyboard(),
            )
            self.user_data[user_id]["state"] = "title"
            return TITLE

    async def handle_confirm_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка подтверждения возврата."""
        text: str = update.message.text.lower()

        if text in ["да", "yes", "ок", "окей", "вернуться"]:
            user_id: int = update.effective_user.id
            if user_id in self.user_data:
                self.user_data[user_id]["photos"] = []

                if self.user_data[user_id].get("size_option"):
                    rows: int = self.user_data[user_id]["rows"]
                    cols: int = self.user_data[user_id]["cols"]
                    photos_per_page: int = rows * cols

                    await update.message.reply_text(
                        self.messages.get_photos_deleted_message()
                        + f"\n\n📍 Фото на странице: *{photos_per_page}*\n\n"
                        + "📏 Выберите размер фотографий в таблице:",
                        parse_mode="Markdown",
                        reply_markup=Keyboards.create_size_keyboard(),
                    )
                    self.user_data[user_id]["state"] = "size_selection"
                    return SIZE_OPTION
                else:
                    await update.message.reply_text(
                        self.messages.get_back_to_title_message(),
                        parse_mode="Markdown",
                        reply_markup=Keyboards.create_title_keyboard(),
                    )
                    self.user_data[user_id]["state"] = "title"
                    return TITLE
        else:
            await update.message.reply_text(
                self.messages.get_return_cancelled_message(),
                reply_markup=Keyboards.create_upload_keyboard(),
            )
            self.user_data[user_id]["state"] = "upload_photos"
            return PHOTOS

    async def done_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Завершение загрузки фото."""
        user_id: int = update.effective_user.id

        logger.info(f"=== ВЫЗВАНА КОМАНДА /done от пользователя {user_id} ===")
        logger.info(f"Пользователь в данных: {user_id in self.user_data}")

        if user_id not in self.user_data:
            logger.warning(f"Пользователь {user_id} не найден в данных")
            await update.message.reply_text(
                self.messages.get_session_expired_message(),
                reply_markup=Keyboards.create_start_keyboard(),
            )
            return ConversationHandler.END

        photos_count: int = len(self.user_data[user_id]["photos"])
        logger.info(f"Количество загруженных фото: {photos_count}")

        if photos_count == 0:
            await update.message.reply_text(
                self.messages.get_no_photos_error(),
                reply_markup=Keyboards.create_upload_keyboard(),
            )
            return PHOTOS

        rows: int = self.user_data[user_id]["rows"]
        cols: int = self.user_data[user_id]["cols"]
        page_info: Dict = calculate_pages_info(photos_count, rows, cols)

        confirmation_text: str = self.messages.get_confirmation_message(
            title=self.user_data[user_id]["title"],
            photos_count=photos_count,
            rows=rows,
            cols=cols,
            size_option=self.user_data[user_id]["size_option"],
            page_info=page_info,
        )

        logger.info("Отправляем подтверждение пользователю с клавиатурой")
        await update.message.reply_text(
            confirmation_text,
            parse_mode="Markdown",
            reply_markup=Keyboards.create_confirmation_keyboard(),
        )

        logger.info("Переход в состояние CONFIRM")
        self.user_data[user_id]["state"] = "confirmation"
        return CONFIRM

    async def handle_confirm_yes(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка кнопки 'Да, всё верно'."""
        user_id: int = update.effective_user.id

        if user_id not in self.user_data:
            await update.message.reply_text(
                self.messages.get_session_expired_message(),
                reply_markup=Keyboards.create_start_keyboard(),
            )
            return ConversationHandler.END

        await self.create_document_from_text(update, context, user_id)
        return ConversationHandler.END

    async def handle_confirm_no(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка кнопки 'Нет, начать заново'."""
        user_id: int = update.effective_user.id

        await update.message.reply_text(
            self.messages.get_confirm_cancelled_message(),
            reply_markup=Keyboards.create_start_keyboard(),
        )
        self.cleanup_user_data(user_id)
        return ConversationHandler.END

    async def create_document_from_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
    ) -> None:
        """Создает документ из текстового подтверждения."""
        await self._create_and_send_document(context, user_id)

    async def _create_and_send_document(self, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
        """Общая логика создания и отправки документа с явным прогрессом."""
        try:
            logger.info(f"=== НАЧАЛО СОЗДАНИЯ ДОКУМЕНТА для пользователя {user_id} ===")

            if user_id not in self.user_data:
                logger.warning(f"Пользователь {user_id} не найден в данных")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=self.messages.get_session_expired_message(),
                    parse_mode="Markdown",
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text=self.messages.get_start_prompt(),
                    reply_markup=Keyboards.create_start_keyboard(),
                )
                return

            photos_count: int = len(self.user_data[user_id]["photos"])
            rows: int = self.user_data[user_id]["rows"]
            cols: int = self.user_data[user_id]["cols"]
            page_info: Dict = calculate_pages_info(photos_count, rows, cols)

            logger.info(
                f"Параметры документа: {photos_count} фото, таблица {rows}×{cols}, "
                f"{page_info['total_pages']} страниц"
            )

            if photos_count > BotConfig.max_photos:
                logger.warning(f"Слишком много фото: {photos_count} > {BotConfig.max_photos}")
                error_text: str = self.messages.get_too_many_photos_error(
                    photos_count, BotConfig.max_photos
                )

                await context.bot.send_message(
                    chat_id=user_id, text=error_text, parse_mode="Markdown"
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text=self.messages.get_start_prompt(),
                    reply_markup=Keyboards.create_start_keyboard(),
                )
                return

            creating_text: str = self.messages.get_creating_document_message_with_progress(
                photos_count, rows, cols, page_info, progress=10
            )
            creating_message = await context.bot.send_message(
                chat_id=user_id,
                text=creating_text,
                parse_mode="Markdown",
                reply_markup=Keyboards.create_wait_keyboard(),
            )

            await context.bot.send_chat_action(
                chat_id=user_id, action=ChatAction.UPLOAD_DOCUMENT
            )

            logger.info("Создаю DocumentCreator...")
            creator: DocumentCreator = DocumentCreator(
                title=self.user_data[user_id]["title"],
                rows=rows,
                cols=cols,
                size_option=self.user_data[user_id]["size_option"],
            )

            logger.info(f"Начинаю создание документа из {photos_count} фото...")
            document_bytes: bytes = creator.create_multi_page_document(
                self.user_data[user_id]["photos"]
            )

            doc_size_mb: float = len(document_bytes) / 1024 / 1024
            logger.info(f"Документ создан: {doc_size_mb:.2f} MB")

            if doc_size_mb > 45:
                logger.error(f"Документ слишком большой: {doc_size_mb:.2f} MB")
                error_text: str = self.messages.get_document_too_big_error(doc_size_mb)

                await context.bot.send_message(
                    chat_id=user_id,
                    text=error_text,
                    parse_mode="Markdown",
                    reply_markup=Keyboards.create_start_keyboard(),
                )

                self.cleanup_user_data(user_id)
                return

            sending_text: str = self.messages.get_sending_document_message_with_progress(
                doc_size_mb, progress=50
            )

            sending_message = await context.bot.send_message(
                chat_id=user_id,
                text=sending_text,
                parse_mode="Markdown",
                reply_markup=Keyboards.create_wait_keyboard(),
            )

            file_caption: str = self.messages.get_document_caption(
                title=self.user_data[user_id]["title"],
                photos_count=photos_count,
                rows=rows,
                cols=cols,
                size_option=self.user_data[user_id]["size_option"],
                page_info=page_info,
            )

            filename: str = self.messages.generate_filename(
                title=self.user_data[user_id]["title"],
                photos_count=photos_count,
                rows=rows,
                cols=cols,
            )

            self.cleanup_user_data(user_id)

            try:
                sent_document = await context.bot.send_document(
                    chat_id=user_id,
                    document=document_bytes,
                    filename=filename,
                    caption=file_caption,
                    parse_mode="Markdown",
                    read_timeout=300,
                    write_timeout=300,
                    connect_timeout=120,
                )
                logger.info("✅ Документ успешно отправлен!")

                file_sent_text: str = self.messages.get_file_sent_message(progress=80)
                file_sent_message = await context.bot.send_message(
                    chat_id=user_id,
                    text=file_sent_text,
                    parse_mode="Markdown",
                    reply_markup=Keyboards.create_wait_keyboard(),
                )

                await asyncio.sleep(1)

                success_text: str = self.messages.get_document_success_message_with_progress(
                    photos_count, rows, cols, page_info, doc_size_mb, progress=100
                )
                success_message = await context.bot.send_message(
                    chat_id=user_id,
                    text=success_text,
                    parse_mode="Markdown",
                    reply_markup=Keyboards.create_start_keyboard(),
                )

            except telegram.error.TimedOut:
                logger.error("Таймаут при отправке документа в Telegram")
                error_text: str = self.messages.get_timeout_error(doc_size_mb)
                await context.bot.send_message(
                    chat_id=user_id,
                    text=error_text,
                    parse_mode="Markdown",
                    reply_markup=Keyboards.create_start_keyboard(),
                )

            except telegram.error.BadRequest as e:
                logger.error(f"Ошибка BadRequest при отправке: {e}")
                if "file is too big" in str(e).lower():
                    error_text: str = self.messages.get_file_too_big_error(doc_size_mb)
                else:
                    error_text: str = self.messages.get_generic_api_error(str(e))

                await context.bot.send_message(
                    chat_id=user_id,
                    text=error_text,
                    parse_mode="Markdown",
                    reply_markup=Keyboards.create_start_keyboard(),
                )

        except telegram.error.TimedOut:
            logger.error("Таймаут при создании/отправке документа")
            error_text: str = self.messages.get_creation_timeout_error()
            await context.bot.send_message(
                chat_id=user_id,
                text=error_text,
                parse_mode="Markdown",
                reply_markup=Keyboards.create_start_keyboard(),
            )
            self.cleanup_user_data(user_id)

        except Exception as e:
            logger.error(f"Ошибка при создании документа: {e}", exc_info=True)
            error_text: str = self.messages.get_generic_creation_error(str(e))
            await context.bot.send_message(
                chat_id=user_id,
                text=error_text,
                parse_mode="Markdown",
                reply_markup=Keyboards.create_start_keyboard(),
            )
            self.cleanup_user_data(user_id)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отмена диалога."""
        user_id: int = update.effective_user.id
        self.cleanup_user_data(user_id)

        await update.message.reply_text(
            self.messages.get_operation_cancelled_message(),
            reply_markup=Keyboards.create_start_keyboard(),
        )
        return ConversationHandler.END

    async def cleanup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Ручная очистка данных пользователя."""
        user_id: int = update.effective_user.id

        if user_id not in self.user_data:
            await update.message.reply_text(
                self.messages.get_no_data_to_clean_message(),
                reply_markup=Keyboards.create_start_keyboard(),
            )
            return

        photos_count: int = len(self.user_data[user_id].get("photos", []))
        self.user_data[user_id]["photos"] = []

        await update.message.reply_text(
            self.messages.get_photos_cleared_message(photos_count),
            reply_markup=Keyboards.create_upload_keyboard(),
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показывает статус бота - адаптивный под текущее состояние."""
        user_id: int = update.effective_user.id

        if user_id not in self.user_data:
            total_users: int = len(self.user_data)
            total_photos: int = sum(
                len(data.get("photos", [])) for data in self.user_data.values()
            )

            await update.message.reply_text(
                self.messages.get_bot_status_message(
                    total_users, total_photos, datetime.now().strftime("%H:%M:%S")
                ),
                parse_mode="Markdown",
                reply_markup=Keyboards.create_start_keyboard(),
            )
        else:
            user_data = self.user_data[user_id]
            state: str = user_data.get("state", "start")
            photos_count: int = len(user_data.get("photos", []))

            status_text: str = "📊 *Статус вашей сессии:*\n\n"

            if state == "upload_photos":
                rows: int = user_data["rows"]
                cols: int = user_data["cols"]
                photos_per_page: int = rows * cols
                total_pages: int = (photos_count + photos_per_page - 1) // photos_per_page

                status_text += self.messages.get_session_status_upload_message(
                    photos_count, rows, cols, photos_per_page, total_pages, user_data["title"]
                )
                reply_keyboard = Keyboards.create_upload_keyboard()

            elif state == "size_selection":
                status_text += self.messages.get_session_status_size_selection_message(
                    user_data["rows"], user_data["cols"], user_data["title"]
                )
                reply_keyboard = Keyboards.create_input_keyboard()

            elif state in ["rows_input", "cols_input"]:
                status_text += self.messages.get_session_status_table_setup_message(
                    user_data["title"]
                )
                reply_keyboard = Keyboards.create_input_keyboard()

            elif state == "title":
                status_text += self.messages.get_session_status_title_message()
                reply_keyboard = Keyboards.create_title_keyboard()

            else:
                status_text += self.messages.get_session_status_ready_message()
                reply_keyboard = Keyboards.create_start_keyboard()

            await update.message.reply_text(
                status_text, parse_mode="Markdown", reply_markup=reply_keyboard
            )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Справка по боту."""
        user_id: int = update.effective_user.id

        help_text: str = self.messages.get_help_message(
            self.config.max_rows, self.config.max_cols, self.config.max_photos
        )

        if user_id in self.user_data:
            state: str = self.user_data[user_id].get("state", "start")
            if state == "upload_photos":
                reply_keyboard = Keyboards.create_upload_keyboard()
            elif state == "title":
                reply_keyboard = Keyboards.create_title_keyboard()
            elif state == "confirmation":
                reply_keyboard = Keyboards.create_confirmation_keyboard()
            else:
                reply_keyboard = Keyboards.create_input_keyboard()
        else:
            reply_keyboard = Keyboards.create_start_keyboard()

        await update.message.reply_text(
            help_text, parse_mode="Markdown", reply_markup=reply_keyboard
        )

    def cleanup_user_data(self, user_id: int) -> None:
        """Очищает данные пользователя из памяти."""
        if user_id in self.user_data:
            if "photos" in self.user_data[user_id]:
                self.user_data[user_id]["photos"] = []
            asyncio.create_task(self._delayed_cleanup(user_id))

    async def _delayed_cleanup(self, user_id: int, delay: int = 3600) -> None:
        """Отложенная очистка данных пользователя."""
        await asyncio.sleep(delay)
        if user_id in self.user_data:
            del self.user_data[user_id]
            logger.info(f"Очищены данные пользователя {user_id}")

    async def periodic_cleanup(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Периодическая очистка старых данных."""
        current_time: datetime = datetime.now()
        users_to_clean: List[int] = []

        for user_id, data in self.user_data.items():
            if "created_at" in data:
                age: float = (current_time - data["created_at"]).total_seconds()
                if age > self.config.session_timeout:
                    users_to_clean.append(user_id)

        for user_id in users_to_clean:
            self.cleanup_user_data(user_id)
            logger.info(f"Автоматически очищены данные пользователя {user_id}")

    def get_conversation_handler(self) -> ConversationHandler:
        """Возвращает настроенный ConversationHandler."""
        return ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                TITLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_title),
                    MessageHandler(
                        filters.TEXT & filters.Regex(r"^(Без заголовка|◀️ Назад)$"),
                        self.handle_conversation_buttons,
                    ),
                ],
                ROWS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_rows),
                    MessageHandler(
                        filters.TEXT & filters.Regex(r"^(◀️ Назад|📊 Статус|❓ Помощь)$"),
                        self.handle_conversation_buttons,
                    ),
                ],
                COLS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_cols),
                    MessageHandler(
                        filters.TEXT & filters.Regex(r"^(◀️ Назад|📊 Статус|❓ Помощь)$"),
                        self.handle_conversation_buttons,
                    ),
                ],
                SIZE_OPTION: [
                    CallbackQueryHandler(self.size_option, pattern="^size_"),
                    MessageHandler(
                        filters.TEXT & filters.Regex(r"^(◀️ Назад|📊 Статус|❓ Помощь)$"),
                        self.handle_conversation_buttons,
                    ),
                ],
                PHOTOS: [
                    MessageHandler(filters.PHOTO | filters.Document.IMAGE, self.get_photo),
                    MessageHandler(
                        filters.TEXT
                        & filters.Regex(
                            r"^(✅ Готово|◀️ Назад|🧹 Очистить|📊 Статус|❓ Помощь)$"
                        ),
                        self.handle_conversation_buttons,
                    ),
                ],
                CONFIRM: [
                    MessageHandler(
                        filters.TEXT
                        & filters.Regex(
                            r"^(✅ Да, всё верно|❌ Нет, начать заново|◀️ Назад|📊 Статус|❓ Помощь)$"
                        ),
                        self.handle_conversation_buttons,
                    ),
                ],
                CONFIRM_BACK: [MessageHandler(filters.TEXT, self.handle_confirm_back)],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CommandHandler("start", self.start),
                MessageHandler(filters.TEXT & filters.Regex(r"^(🟢 Начать)$"), self.start),
            ],
            conversation_timeout=7200,
            allow_reentry=True,
        )

    async def handle_conversation_buttons(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[int]:
        """Обработчик кнопок внутри ConversationHandler."""
        text: str = update.message.text
        user_id: int = update.effective_user.id

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

    def get_callback_handlers(self) -> List[CallbackQueryHandler]:
        """Возвращает обработчики callback-запросов."""
        return [
            CallbackQueryHandler(self.size_option, pattern="^size_"),
        ]

    def get_command_handlers(self) -> List[CommandHandler]:
        """Возвращает список обработчиков команд."""
        return [
            CommandHandler("cleanup", self.cleanup_command),
            CommandHandler("status", self.status_command),
            CommandHandler("help", self.help_command),
        ]
    