.PHONY: help init venv install install-dev setup-env run bot clean lint format quick-check \
        docker-build docker-run docker-clean docker-down docker-logs docker-shell \
        version check check-python-version uv-install

# Цвета для вывода
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
CYAN := \033[0;36m
NC := \033[0m # No Color

# Переменные
PYTHON := python3.12
UV := uv
PACKAGE_NAME := appraiser-photo-bot
ENV_FILE := .env
ENV_EXAMPLE := .env.example
VENV_DIR = .venv

help: ## Показать это сообщение
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)🤖 ДОСТУПНЫЕ КОМАНДЫ$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo ""
	@echo "$(GREEN)🚀 Быстрый старт:$(NC)"
	@echo "  1. make venv                 # Создать виртуальное окружение"
	@echo "  2. source .venv/bin/activate # Активировать venv"
	@echo "  3. make install              # Установить зависимости"
	@echo "  4. make setup-env            # Настроить .env файл"
	@echo "  5. make bot                  # Запустить бота"
	@echo ""
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(GREEN)📦 Управление проектом:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

# ===== УСТАНОВКА UV =====
uv-install: ## Установить uv (если не установлен)
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)📦 УСТАНОВКА UV$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@if ! command -v $(UV) > /dev/null; then \
		echo "$(YELLOW)Устанавливаю uv...$(NC)"; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		echo "$(GREEN)✅ uv установлен!$(NC)"; \
	else \
		echo "$(GREEN)✅ uv уже установлен$(NC)"; \
	fi
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

# ===== ОСНОВНЫЕ КОМАНДЫ =====
venv: check-python-version ## Создать виртуальное окружение через uv
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)🔧 СОЗДАНИЕ ВИРТУАЛЬНОГО ОКРУЖЕНИЯ$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@if [ ! -d ".venv" ]; then \
		echo "$(YELLOW)Создаю виртуальное окружение через uv...$(NC)"; \
		if command -v $(UV) > /dev/null; then \
			$(UV) venv --python $(PYTHON) .venv; \
		else \
			echo "$(YELLOW)uv не найден, использую стандартный venv...$(NC)"; \
			$(PYTHON) -m venv .venv; \
		fi; \
		echo "$(GREEN)✅ Виртуальное окружение создано в .venv$(NC)"; \
		echo "$(YELLOW)Активируйте: source .venv/bin/activate$(NC)"; \
	else \
		echo "$(YELLOW)Виртуальное окружение уже существует в .venv$(NC)"; \
	fi
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

check-python-version: ## Проверить версию Python
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)🐍 ПРОВЕРКА PYTHON$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@if command -v $(PYTHON) > /dev/null; then \
		echo "$(GREEN)✅ $(PYTHON) найден: $$($(PYTHON) --version)$(NC)"; \
	elif command -v python3.12 > /dev/null; then \
		echo "$(YELLOW)⚠️ Использую python3.12 вместо $(PYTHON)$(NC)"; \
		PYTHON := python3.12; \
	elif command -v python3 > /dev/null; then \
		echo "$(YELLOW)⚠️ Использую python3$(NC)"; \
		PYTHON := python3; \
	else \
		echo "$(RED)❌ Python не найден! Установите Python 3.12$(NC)"; \
		exit 1; \
	fi
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

install: check-python-version ## Установить зависимости
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)📥 УСТАНОВКА ЗАВИСИМОСТЕЙ$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "$(RED)❌ ОШИБКА: Виртуальное окружение не активировано!$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Активируйте окружение:$(NC)"; \
		echo "  $(GREEN)source .venv/bin/activate$(NC)"; \
		echo ""; \
		exit 1; \
	fi
	
	@# Явно указываем uv использовать Python из venv
	@if command -v $(UV) > /dev/null; then \
		echo "$(YELLOW)Установка через uv...$(NC)"; \
		UV_PYTHON="$(VENV_DIR)/bin/python" $(UV) pip install -e . -q; \
	else \
		echo "$(YELLOW)uv не найден, использую pip...$(NC)"; \
		$(VENV_DIR)/bin/python -m pip install -e .; \
	fi
	
	@echo "$(GREEN)✅ Зависимости установлены в $(VENV_DIR)$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

install-dev: ## Установить зависимости для разработки через uv
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)🛠️ УСТАНОВКА DEV-ЗАВИСИМОСТЕЙ$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@if command -v $(UV) > /dev/null && [ -f ".venv/bin/python" ]; then \
		$(UV) pip install -e ".[dev]" -q; \
	elif [ -n "$$VIRTUAL_ENV" ]; then \
		echo "$(YELLOW)Использую pip из активного окружения...$(NC)"; \
		pip install -e ".[dev]" -q; \
	else \
		echo "$(YELLOW)uv не найден, использую pip...$(NC)"; \
		pip install -e ".[dev]"; \
	fi
	@echo "$(GREEN)✅ Dev-зависимости установлены$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

setup-env: ## Настроить файл окружения
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)⚙️ НАСТРОЙКА ОКРУЖЕНИЯ$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@if [ ! -f $(ENV_EXAMPLE) ]; then \
		echo "$(RED)❌ Файл $(ENV_EXAMPLE) не найден!$(NC)"; \
		exit 1; \
	fi
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "$(YELLOW)Создаю файл $(ENV_FILE) из примера...$(NC)"; \
		cp $(ENV_EXAMPLE) $(ENV_FILE); \
		echo "$(GREEN)✅ Файл $(ENV_FILE) создан. Отредактируйте его.$(NC)"; \
	else \
		echo "$(YELLOW)Файл $(ENV_FILE) уже существует.$(NC)"; \
	fi
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

run: ## Запустить бота
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)🤖 ЗАПУСК БОТА$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@appraiser-photo-bot

bot: setup-env run ## Запустить бота с проверкой окружения

# ===== ОЧИСТКА =====
clean: ## Очистить временные файлы
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)🧹 ОЧИСТКА ПРОЕКТА$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	
	@# Спросить подтверждение на удаление .venv
	@if [ -d ".venv" ]; then \
		printf "$(YELLOW)Удалить виртуальное окружение .venv? (y/n): $(NC)"; \
		read choice; \
		if [ "$$choice" = "y" ] || [ "$$choice" = "Y" ]; then \
			rm -rf .venv; \
			printf "$(GREEN)✓ Виртуальное окружение удалено$(NC)\n"; \
		fi; \
	fi
	
	@# Очистка кэша Python
	@printf "$(YELLOW)Очистка кэша Python...$(NC)\n"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	
	@# Очистка кэша инструментов
	@rm -rf .ruff_cache 2>/dev/null || true
	
	@# Очистка файлов сборки
	@rm -rf dist build *.egg-info 2>/dev/null || true
	
	@# Очистка uv кэша (опционально)
	@if command -v $(UV) > /dev/null; then \
		printf "$(YELLOW)Очистить кэш uv? (y/n): $(NC)"; \
		read choice; \
		if [ "$$choice" = "y" ] || [ "$$choice" = "Y" ]; then \
			$(UV) cache clean; \
			printf "$(GREEN)✓ Кэш uv очищен$(NC)\n"; \
		fi; \
	fi
	
	@printf "$(GREEN)✓ Очистка завершена!$(NC)\n"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

# ===== ПРОВЕРКИ КОДА =====
lint: ## Проверить код с помощью ruff
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)🔍 ПРОВЕРКА КОДА$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@ruff check .
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

format: ## Форматировать код с помощью ruff
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)✨ ФОРМАТИРОВАНИЕ КОДА$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@ruff format .
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

format-imports: ## Отсортировать импорты
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)📋 СОРТИРОВКА ИМПОРТОВ$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@ruff check . --fix --select I001
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

quick-check: format-imports format ## Отсортировать импорты и отформатировать код
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(GREEN)✅ Код отформатирован и импорты отсортированы$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

# ===== DOCKER =====
docker-build: ## Собрать Docker образ
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)🐳 СБОРКА DOCKER ОБРАЗА$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@docker build -t $(PACKAGE_NAME) .
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

docker-run: ## Запустить в Docker
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)🐳 ЗАПУСК В DOCKER$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@docker run --env-file $(ENV_FILE) --rm $(PACKAGE_NAME)

docker-clean: ## Очистить Docker образы
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)🐳 ОЧИСТКА DOCKER$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@docker rmi $(PACKAGE_NAME) 2>/dev/null || true
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

docker-down: ## Остановить Docker контейнеры
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)🐳 ОСТАНОВКА КОНТЕЙНЕРОВ$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@docker-compose down 2>/dev/null || true
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

docker-logs: ## Показать логи Docker
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)🐳 ЛОГИ DOCKER$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@docker-compose logs -f 2>/dev/null || true

docker-shell: ## Зайти в shell Docker контейнера
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)🐳 SHELL В КОНТЕЙНЕРЕ$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@docker run -it --rm --entrypoint /bin/bash $(PACKAGE_NAME)

# ===== ВСПОМОГАТЕЛЬНЫЕ =====
version: ## Показать версию пакета
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)📌 ВЕРСИЯ ПАКЕТА$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@python -c "from appraiser_photo_bot import __version__; print(f'Версия: {__version__}')" 2>/dev/null || echo "$(RED)❌ Не удалось получить версию$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

check: check-python-version ## Проверить систему
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@echo "$(YELLOW)🔧 ПРОВЕРКА СИСТЕМЫ$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"
	@if command -v $(UV) > /dev/null; then \
		echo "$(GREEN)✅ uv установлен: $$($(UV) --version)$(NC)"; \
	else \
		echo "$(YELLOW)⚠️ uv не установлен (установите: make uv-install)$(NC)"; \
	fi
	@if [ -d ".venv" ]; then \
		echo "$(GREEN)✅ Виртуальное окружение найдено$(NC)"; \
	else \
		echo "$(YELLOW)⚠️ Виртуальное окружение не найдено (make venv)$(NC)"; \
	fi
	@which appraiser-photo-bot > /dev/null && echo "$(GREEN)✅ CLI команда доступна$(NC)" || echo "$(YELLOW)⚠️ CLI команда не найдена (установите пакет)$(NC)"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)\n"

.DEFAULT_GOAL := help