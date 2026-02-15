"""Основной модуль бота."""

import logging
from typing import Any, Optional

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters

from .config import BotConfig
from .document_creators.messages import MessageGenerator
from .handlers import BotHandlers
from .keyboards import Keyboards

logger = logging.getLogger(__name__)


class PhotoTableBot:
    """Основной класс бота."""

    def __init__(self, config: BotConfig) -> None:
        self.config: BotConfig = config
        self.handlers: BotHandlers = BotHandlers(config)
        self.application: Optional[Any] = None
        self.message_generator: MessageGenerator = MessageGenerator()

    async def _setup_periodic_tasks(self, application: Any) -> None:
        """Настраивает периодические задачи."""
        application.job_queue.run_repeating(
            self.handlers.periodic_cleanup,
            interval=self.config.cleanup_interval,
            first=10,
        )
        logger.info("Периодические задачи настроены")

    async def post_init(self, application: Any) -> None:
        """Выполняется после инициализации бота."""
        try:
            commands = [
                ("start", "Начать создание документа"),
                ("help", "Помощь по боту"),
                ("status", "Статус бота"),
                ("cleanup", "Очистить память бота"),
            ]

            await application.bot.set_my_commands(commands)
            logger.info("Команды меню бота установлены")

            if self.config.admin_id:
                try:
                    await application.bot.send_message(
                        chat_id=self.config.admin_id,
                        text=self.message_generator.get_admin_notification(),
                    )
                    logger.info(f"Уведомление отправлено админу {self.config.admin_id}")
                except Exception as e:
                    logger.warning(f"Не удалось уведомить админа: {e}")

        except Exception as e:
            logger.error(f"Ошибка в post_init: {e}")

    def setup_handlers(self) -> None:
        """Настраивает все обработчики в правильном порядке."""
        logger.info("=== НАСТРОЙКА ОБРАБОТЧИКОВ ===")

        conv_handler = self.handlers.get_conversation_handler()
        logger.info("1. ✅ Добавляем ConversationHandler")
        self.application.add_handler(conv_handler)

        callback_handlers = self.handlers.get_callback_handlers()
        logger.info(f"2. ✅ Добавляем {len(callback_handlers)} callback-обработчиков")
        for handler in callback_handlers:
            self.application.add_handler(handler)

        command_handlers = self.handlers.get_command_handlers()
        logger.info(f"3. ✅ Добавляем {len(command_handlers)} обработчиков команд")
        for handler in command_handlers:
            self.application.add_handler(handler)

        if self.config.enable_buttons:
            button_handler = self.handlers.get_button_handler()
            if button_handler:
                logger.info("4. ✅ Добавляем обработчик кнопок, доступных всегда")
                self.application.add_handler(button_handler)

        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_unknown_message,
            )
        )

        logger.info("✅ Все обработчики успешно добавлены")

    async def handle_unknown_message(self, update: Update, context: Any) -> None:
        """Обработчик неизвестных текстовых сообщений."""
        try:
            user_id = update.effective_user.id
            text = update.message.text

            logger.info(f"Пользователь {user_id} отправил неизвестное сообщение: '{text}'")

            state: str = "start"
            if user_id in self.handlers.user_data:
                state = self.handlers.user_data[user_id].get("state", "start")

            message_text = self.message_generator.get_unknown_message_text(state, self.config.enable_buttons)

            if self.config.enable_buttons:
                reply_markup = Keyboards.create_start_keyboard()
                if state == "upload_photos":
                    reply_markup = Keyboards.create_upload_keyboard()
                elif state == "confirmation":
                    reply_markup = Keyboards.create_confirmation_keyboard()
                elif state == "title":
                    reply_markup = Keyboards.create_title_keyboard()
                elif state in ["rows_input", "cols_input", "size_selection"]:
                    reply_markup = Keyboards.create_input_keyboard()

                await update.message.reply_text(
                    message_text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup,
                )
            else:
                await update.message.reply_text(message_text, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Ошибка в handle_unknown_message: {e}")
            try:
                await update.message.reply_text(
                    self.message_generator.get_simple_error_message(),
                    parse_mode="Markdown",
                )
            except Exception:
                pass

    async def error_handler(self, update: Update, context: Any) -> None:
        """Глобальный обработчик ошибок."""
        logger.error(f"Ошибка: {context.error}", exc_info=True)

        try:
            error_msg: str = str(context.error)[:200]
            message_text = self.message_generator.get_error_message_text(error_msg, self.config.enable_buttons)

            reply_markup = None
            if self.config.enable_buttons and update.effective_user:
                user_id = update.effective_user.id
                if user_id in self.handlers.user_data:
                    state = self.handlers.user_data[user_id].get("state", "start")
                    if state == "upload_photos":
                        reply_markup = Keyboards.create_upload_keyboard()
                    elif state == "confirmation":
                        reply_markup = Keyboards.create_confirmation_keyboard()
                    elif state == "title":
                        reply_markup = Keyboards.create_title_keyboard()
                    elif state in ["rows_input", "cols_input", "size_selection"]:
                        reply_markup = Keyboards.create_input_keyboard()
                    else:
                        reply_markup = Keyboards.create_start_keyboard()
                else:
                    reply_markup = Keyboards.create_start_keyboard()

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message_text,
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения об ошибке: {e}")

    def run(self) -> None:
        """Запускает бота."""
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.DEBUG if self.config.debug else logging.INFO,
        )

        self.application = (
            ApplicationBuilder()
            .token(self.config.token)
            .read_timeout(60)
            .write_timeout(60)
            .connect_timeout(30)
            .pool_timeout(30)
            .post_init(self.post_init)
            .build()
        )

        self.application.add_error_handler(self.error_handler)

        self.setup_handlers()

        self.application.job_queue.run_once(
            lambda ctx: self._setup_periodic_tasks(self.application),
            when=0,
        )

        logger.info("=" * 60)
        logger.info("🤖 БОТ ЗАПУЩЕН")
        logger.info(f"   Режим отладки: {'ВКЛ' if self.config.debug else 'ВЫКЛ'}")
        logger.info(f"   Кнопки меню: {'ВКЛ' if self.config.enable_buttons else 'ВЫКЛ'}")
        logger.info(f"   Таймаут сессии: {self.config.session_timeout} сек")
        logger.info(f"   Интервал очистки: {self.config.cleanup_interval} сек")
        logger.info("=" * 60)

        if self.config.enable_buttons:
            logger.info("📱 Доступные кнопки:")
            logger.info("   🟢 Начать | ◀️ Назад | ✅ Готово | 🧹 Очистить")
            logger.info("   📊 Статус | ❓ Помощь | 📝 Без заголовка")
            logger.info("   ✅ Да, всё верно | ❌ Нет, начать заново")
            logger.info("=" * 60)

        try:
            self.application.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES,
                close_loop=False,
            )
        except KeyboardInterrupt:
            logger.info("⏹️ Бот остановлен пользователем")
        except Exception as e:
            logger.error(f"💥 Критическая ошибка при работе бота: {e}", exc_info=True)
            raise
