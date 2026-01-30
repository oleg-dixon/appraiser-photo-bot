import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from telegram import Update
from handlers import BotHandlers
from config import BotConfig

logger = logging.getLogger(__name__)

class PhotoTableBot:
    """Основной класс бота"""
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.handlers = BotHandlers(config)
        self.application = None
    
    async def _setup_periodic_tasks(self, application):
        """Настраивает периодические задачи"""
        # Периодическая очистка старых данных
        application.job_queue.run_repeating(
            self.handlers.periodic_cleanup,
            interval=self.config.cleanup_interval,
            first=10
        )
        logger.info("Периодические задачи настроены")
    
    async def post_init(self, application):
        """Выполняется после инициализации бота"""
        try:
            # Устанавливаем команды меню бота
            commands = [
                ("start", "Начать создание документа"),
                ("help", "Помощь по боту"),
                ("status", "Статус бота"),
                ("cleanup", "Очистить память бота")
            ]
            
            await application.bot.set_my_commands(commands)
            logger.info("Команды меню бота установлены")
            
            # Отправляем сообщение админу о запуске (если указан)
            if self.config.admin_id:
                try:
                    await application.bot.send_message(
                        chat_id=self.config.admin_id,
                        text="✅ Бот успешно запущен с поддержкой кнопок!"
                    )
                    logger.info(f"Уведомление отправлено админу {self.config.admin_id}")
                except Exception as e:
                    logger.warning(f"Не удалось уведомить админа: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка в post_init: {e}")
    
    def setup_handlers(self):
        """Настраивает все обработчики в правильном порядке"""
        logger.info("=== НАСТРОЙКА ОБРАБОТЧИКОВ ===")
        
        # ВАЖНО: Правильный порядок добавления обработчиков
        # 1. Сначала ConversationHandler (обрабатывает все сообщения внутри диалога)
        # 2. Затем callback-обработчики
        # 3. Затем обработчики команд
        # 4. Затем обработчик кнопок, доступных всегда
        # 5. В конце обработчик неизвестных сообщений
        
        # 1. ConversationHandler - ПЕРВЫЙ
        conv_handler = self.handlers.get_conversation_handler()
        logger.info("1. ✅ Добавляем ConversationHandler")
        self.application.add_handler(conv_handler)
        
        # 2. Callback-обработчики
        callback_handlers = self.handlers.get_callback_handlers()
        logger.info(f"2. ✅ Добавляем {len(callback_handlers)} callback-обработчиков")
        for handler in callback_handlers:
            self.application.add_handler(handler)
        
        # 3. Обработчики команд
        command_handlers = self.handlers.get_command_handlers()
        logger.info(f"3. ✅ Добавляем {len(command_handlers)} обработчиков команд")
        for handler in command_handlers:
            self.application.add_handler(handler)
        
        # 4. Обработчик кнопок, доступных всегда (только вне диалога)
        if self.config.enable_buttons:
            button_handler = self.handlers.get_button_handler()
            if button_handler:
                logger.info("4. ✅ Добавляем обработчик кнопок, доступных всегда")
                self.application.add_handler(button_handler)
        
        # 5. Обработчик неизвестных текстовых сообщений
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_unknown_message
            )
        )
        
        logger.info("✅ Все обработчики успешно добавлены")
    
    async def handle_unknown_message(self, update: Update, context):
        """Обработчик неизвестных текстовых сообщений"""
        try:
            from .keyboards import Keyboards
            
            user_id = update.effective_user.id
            text = update.message.text
            
            logger.info(f"Пользователь {user_id} отправил неизвестное сообщение: '{text}'")
            
            # Если включены кнопки - отправляем с клавиатурой
            if self.config.enable_buttons:
                # Проверяем, есть ли активная сессия у пользователя
                if user_id in self.handlers.user_data:
                    state = self.handlers.user_data[user_id].get('state', 'start')
                    
                    # Определяем, какую клавиатуру показать в зависимости от состояния
                    if state == 'upload_photos':
                        reply_markup = Keyboards.create_upload_keyboard()
                        message = "🤔 *Я не понял ваше сообщение*\n\nСейчас ожидаю фотографии. Пожалуйста, отправьте фото или используйте кнопки:"
                    elif state == 'confirmation':
                        reply_markup = Keyboards.create_confirmation_keyboard()
                        message = "🤔 *Я не понял ваше сообщение*\n\nПожалуйста, подтвердите создание документа с помощью кнопок:"
                    elif state == 'title':
                        reply_markup = Keyboards.create_title_keyboard()
                        message = "🤔 *Я не понял ваше сообщение*\n\nПожалуйста, введите заголовок или используйте кнопки:"
                    elif state in ['rows_input', 'cols_input', 'size_selection']:
                        reply_markup = Keyboards.create_input_keyboard()
                        message = "🤔 *Я не понял ваше сообщение*\n\nПожалуйста, следуйте инструкциям или используйте кнопки:"
                    else:
                        reply_markup = Keyboards.create_start_keyboard()
                        message = "🤔 *Я не понял ваше сообщение*\n\nПожалуйста, используйте кнопки меню или команды:"
                else:
                    reply_markup = Keyboards.create_start_keyboard()
                    message = "🤔 *Я не понял ваше сообщение*\n\nДля начала работы нажмите '🟢 Начать':"
                
                await update.message.reply_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                # Если кнопки отключены - отправляем без клавиатуры
                await update.message.reply_text(
                    "🤔 Я не понял ваше сообщение.\n\n"
                    "Используйте команды:\n"
                    "/start - начать создание документа\n"
                    "/help - получить помощь\n"
                    "/status - статус бота\n"
                    "/cleanup - очистить память",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Ошибка в handle_unknown_message: {e}")
            
            # Отправляем простое сообщение об ошибке
            try:
                await update.message.reply_text(
                    "⚠️ Произошла ошибка. Пожалуйста, попробуйте еще раз.",
                    parse_mode='Markdown'
                )
            except:
                pass
    
    async def error_handler(self, update: Update, context):
        """Глобальный обработчик ошибок"""
        logger.error(f"Ошибка: {context.error}", exc_info=True)
        
        try:
            from .keyboards import Keyboards
            
            error_msg = str(context.error)[:200]  # Берем только первые 200 символов
            
            # Определяем, какую клавиатуру показать
            if self.config.enable_buttons:
                # Проверяем, есть ли активная сессия
                if update.effective_user:
                    user_id = update.effective_user.id
                    if user_id in self.handlers.user_data:
                        state = self.handlers.user_data[user_id].get('state', 'start')
                        if state == 'upload_photos':
                            reply_markup = Keyboards.create_upload_keyboard()
                        elif state == 'confirmation':
                            reply_markup = Keyboards.create_confirmation_keyboard()
                        elif state == 'title':
                            reply_markup = Keyboards.create_title_keyboard()
                        elif state in ['rows_input', 'cols_input', 'size_selection']:
                            reply_markup = Keyboards.create_input_keyboard()
                        else:
                            reply_markup = Keyboards.create_start_keyboard()
                    else:
                        reply_markup = Keyboards.create_start_keyboard()
                else:
                    reply_markup = Keyboards.create_start_keyboard()
            else:
                reply_markup = None
            
            # Отправляем сообщение об ошибке пользователю
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ *Произошла ошибка*\n\n"
                     f"`{error_msg}`\n\n"
                     f"Пожалуйста, попробуйте еще раз или начните заново: /start",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения об ошибке: {e}")
    
    def run(self):
        """Запускает бота"""
        # Настраиваем логирование
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.DEBUG if self.config.debug else logging.INFO
        )
        
        # Создаем Application
        self.application = (
            ApplicationBuilder()
            .token(self.config.token)
            .read_timeout(60)
            .write_timeout(60)
            .connect_timeout(30)
            .pool_timeout(30)
            .post_init(self.post_init)  # Добавляем post_init
            .build()
        )
        
        # Добавляем обработчик ошибок
        self.application.add_error_handler(self.error_handler)
        
        # Настраиваем обработчики
        self.setup_handlers()
        
        # Настраиваем периодические задачи
        self.application.job_queue.run_once(
            lambda ctx: self._setup_periodic_tasks(self.application),
            when=0
        )
        
        # Запускаем бота
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
                close_loop=False
            )
        except KeyboardInterrupt:
            logger.info("⏹️ Бот остановлен пользователем")
        except Exception as e:
            logger.error(f"💥 Критическая ошибка при работе бота: {e}", exc_info=True)
            raise