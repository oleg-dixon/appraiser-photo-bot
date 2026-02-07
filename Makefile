.PHONY: help install install-dev setup-env run clean test lint format type-check check-all \
        build publish install-package uninstall docker-build docker-run docker-clean \
        venv venv-create venv-help clean-all init check check-env bot version \
        quick-check lint-fix lint-all check-style docker-down docker-logs docker-shell \
        docker-test update-deps venv-check venv-activate check-python-version

# Цвета для вывода
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Переменные - используем Python 3.12 который у вас точно работает
PYTHON := python3.12
UV := uv
PACKAGE_NAME := appraiser-photo-bot
ENV_FILE := .env
ENV_EXAMPLE := .env.example

help: ## Показать это сообщение
	@echo "$(YELLOW)Доступные команды:$(NC)"
	@echo ""
	@echo "$(GREEN)📦 Управление проектом:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)🚀 Быстрый старт:$(NC)"
	@echo "  1. make init           # Инициализация проекта"
	@echo "  2. source .venv/bin/activate # Активировать venv"
	@echo "  3. make bot            # Запуск бота"
	@echo ""

# ===== ОСНОВНЫЕ КОМАНДЫ =====
init: check-python-version venv install setup-env ## Инициализировать проект (первый запуск)
	@echo "$(GREEN)✅ Проект инициализирован!$(NC)"
	@echo "$(GREEN)✅ Виртуальное окружение создано!$(NC)"
	@echo "$(YELLOW)📝 Не забудьте добавить BOT_TOKEN в файл .env$(NC)"
	@echo ""
	@echo "$(YELLOW)🚀 Дальнейшие шаги:$(NC)"
	@echo "  1. Активируйте виртуальное окружение:"
	@echo "     source .venv/bin/activate"
	@echo ""
	@echo "  2. Проверьте активацию:"
	@echo "     which python"
	@echo ""
	@echo "  3. Запустите бота:"
	@echo "     make run"
	@echo ""
	@echo "$(YELLOW)Или выполните: make bot (после активации venv)$(NC)"

venv: check-python-version ## Создать виртуальное окружение
	@if [ ! -d ".venv" ]; then \
		echo "$(YELLOW)Создаю виртуальное окружение...$(NC)"; \
		if command -v $(PYTHON) > /dev/null; then \
			echo "$(YELLOW)Использую $(PYTHON)...$(NC)"; \
			$(PYTHON) -m venv .venv; \
		elif command -v python3.12 > /dev/null; then \
			echo "$(YELLOW)Использую python3.12...$(NC)"; \
			python3.12 -m venv .venv; \
		elif command -v python3 > /dev/null; then \
			echo "$(YELLOW)Использую python3...$(NC)"; \
			python3 -m venv .venv; \
		else \
			echo "$(RED)❌ Python не найден!$(NC)"; \
			exit 1; \
		fi; \
		if [ $$? -eq 0 ] && [ -f ".venv/bin/activate" ]; then \
			echo "$(GREEN)Виртуальное окружение создано в .venv$(NC)"; \
		else \
			echo "$(RED)❌ Ошибка создания виртуального окружения$(NC)"; \
			echo "$(YELLOW)Попробуйте создать окружение с помощью virtualenv:$(NC)"; \
			echo "  virtualenv .venv --python=$(PYTHON)"; \
			exit 1; \
		fi; \
	else \
		echo "$(YELLOW)Виртуальное окружение уже существует в .venv$(NC)"; \
	fi
	@echo "$(YELLOW)Активируйте его командой:$(NC)"
	@echo "  source .venv/bin/activate  # Linux/Mac"
	@echo "  .venv\\Scripts\\activate     # Windows"

venv-activate: ## Активировать виртуальное окружение
	@if [ -d ".venv" ]; then \
		if [ -f ".venv/bin/activate" ]; then \
			echo "$(YELLOW)Активирую виртуальное окружение...$(NC)"; \
			. .venv/bin/activate && \
			echo "$(GREEN)✅ Виртуальное окружение активировано!$(NC)"; \
			echo "   🐍 Python: $$(python --version 2>&1)"; \
			echo "   📍 Путь: $$(which python)"; \
		else \
			echo "$(RED)❌ Ошибка: .venv/bin/activate не найден$(NC)"; \
			exit 1; \
		fi; \
	else \
		echo "$(RED)❌ Виртуальное окружение не найдено$(NC)"; \
		echo "   Создайте: make venv"; \
		exit 1; \
	fi

venv-check: ## Проверить виртуальное окружение
	@if [ -d ".venv" ]; then \
		echo "$(GREEN)✅ Виртуальное окружение найдено в .venv$(NC)"; \
		if [ -n "$$VIRTUAL_ENV" ]; then \
			echo "$(GREEN)✅ Виртуальное окружение активировано$(NC)"; \
			echo "   Путь: $$VIRTUAL_ENV"; \
			echo "   Python: $$(which python)"; \
		else \
			echo "$(YELLOW)⚠️  Виртуальное окружение не активировано$(NC)"; \
			echo "   Запустите: make venv-activate"; \
		fi; \
	else \
		echo "$(RED)❌ Виртуальное окружение не найдено$(NC)"; \
		echo "   Создайте: make venv"; \
		exit 1; \
	fi

check-python-version: ## Проверить версию Python
	@echo "$(YELLOW)Проверяю доступные версии Python...$(NC)"
	@echo "$(YELLOW)Приоритетная версия: $(PYTHON)$(NC)"
	@if command -v $(PYTHON) > /dev/null; then \
		echo "$(GREEN)✅ $(PYTHON) найден$(NC)"; \
		$(PYTHON) --version; \
	elif command -v python3.12 > /dev/null; then \
		echo "$(YELLOW)⚠️  $(PYTHON) не найден, но найден python3.12$(NC)"; \
		python3.12 --version; \
		echo "$(YELLOW)Использую python3.12 вместо $(PYTHON)$(NC)"; \
	elif command -v python3 > /dev/null; then \
		echo "$(YELLOW)⚠️  $(PYTHON) не найден, но найден python3$(NC)"; \
		python3 --version; \
		echo "$(YELLOW)Использую python3$(NC)"; \
	else \
		echo "$(RED)❌ Python не найден!$(NC)"; \
		echo "$(YELLOW)Установите Python 3.12: brew install python@3.12$(NC)"; \
		exit 1; \
	fi

install: ## Установить зависимости через uv (использует setup.py)
	@echo "$(YELLOW)Устанавливаю зависимости...$(NC)"
	@if command -v $(UV) > /dev/null; then \
		$(UV) pip install -e .; \
	else \
		echo "$(YELLOW)UV не найден, использую pip...$(NC)"; \
		pip install -e .; \
	fi

install-dev: ## Установить зависимости для разработки
	@echo "$(YELLOW)Устанавливаю зависимости для разработки...$(NC)"
	@if command -v $(UV) > /dev/null; then \
		$(UV) pip install -e ".[dev]"; \
	else \
		echo "$(YELLOW)UV не найден, использую pip...$(NC)"; \
		pip install -e ".[dev]"; \
	fi

setup-env: ## Настроить файл окружения
	@if [ ! -f $(ENV_EXAMPLE) ]; then \
		echo "$(RED)Файл $(ENV_EXAMPLE) не найден!$(NC)"; \
		exit 1; \
	fi
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "$(YELLOW)Создаю файл $(ENV_FILE) из примера...$(NC)"; \
		cp $(ENV_EXAMPLE) $(ENV_FILE); \
		echo "$(GREEN)Файл $(ENV_FILE) создан. Отредактируйте его, добавив BOT_TOKEN.$(NC)"; \
	else \
		echo "$(YELLOW)Файл $(ENV_FILE) уже существует.$(NC)"; \
	fi

run: ## Запустить бота через установленный пакет
	@echo "$(YELLOW)Запускаю бота...$(NC)"
	@appraiser-photo-bot

bot: setup-env run ## Запустить бота с проверкой окружения

# ===== ОЧИСТКА =====
clean: ## Очистить временные файлы и кэш
	@echo "$(YELLOW)Очищаю временные файлы...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name ".coverage" -delete
	@find . -type d -name ".vscode" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".hypothesis" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Очистка завершена!$(NC)"

clean-all: clean ## Полная очистка (включая виртуальное окружение)
	@echo "$(YELLOW)Очищаю виртуальное окружение...$(NC)"
	@rm -rf .venv 2>/dev/null || true
	@rm -f uv.lock 2>/dev/null || true

# ===== ПРОВЕРКИ И ТЕСТЫ =====
test: ## Запустить тесты
	@echo "$(YELLOW)Запускаю тесты...$(NC)"
	@pytest tests/ -v --cov=appraiser_photo_bot --cov-report=term-missing

lint: ## Проверить код с помощью ruff
	@echo "$(YELLOW)Проверяю код с помощью ruff...$(NC)"
	@ruff check .

lint-fix: ## Исправить автоматически исправимые проблемы с помощью ruff
	@echo "$(YELLOW)Исправляю автоматически исправимые проблемы...$(NC)"
	@ruff check . --fix

format: ## Форматировать код с помощью ruff
	@echo "$(YELLOW)Форматирую код...$(NC)"
	@ruff format .

check-style: ## Проверить стиль кода с помощью ruff
	@echo "$(YELLOW)Проверяю стиль кода...$(NC)"
	@ruff format . --check

type-check: ## Проверить типы с помощью mypy
	@echo "$(YELLOW)Проверяю типы...$(NC)"
	@mypy appraiser_photo_bot/ document_creators/

quick-check: lint-fix format ## Быстрая проверка и исправление кода

check-all: lint check-style type-check test ## Выполнить все проверки

ci: check-all ## Запустить все проверки для CI/CD

# ===== СБОРКА И ПАКЕТИРОВАНИЕ =====
build: ## Собрать пакет
	@echo "$(YELLOW)Собираю пакет...$(NC)"
	@python -m build
	@echo "$(GREEN)Пакет собран в директории dist/$(NC)"

install-package: build ## Установить локально собранный пакет
	@echo "$(YELLOW)Устанавливаю локальный пакет...$(NC)"
	@pip install dist/$(PACKAGE_NAME)-*.tar.gz

uninstall: ## Удалить пакет
	@echo "$(YELLOW)Удаляю пакет...$(NC)"
	@pip uninstall $(PACKAGE_NAME) -y || true

# ===== DOCKER =====
docker-build: ## Собрать Docker образ (требует Dockerfile)
	@echo "$(YELLOW)Собираю Docker образ...$(NC)"
	@docker build -t $(PACKAGE_NAME) .

docker-run: ## Запустить в Docker (требует Dockerfile)
	@echo "$(YELLOW)Запускаю в Docker...$(NC)"
	@docker run --env-file $(ENV_FILE) --rm $(PACKAGE_NAME)

docker-clean: ## Очистить Docker образы
	@echo "$(YELLOW)Очищаю Docker образы...$(NC)"
	@docker rmi $(PACKAGE_NAME) 2>/dev/null || true

# ===== ВСПОМОГАТЕЛЬНЫЕ =====
version: ## Показать версию пакета
	@python -c "from appraiser_photo_bot import __version__; print(f'Версия: {__version__}')" 2>/dev/null || echo "$(RED)Не удалось получить версию$(NC)"

check: ## Проверить систему
	@echo "$(YELLOW)Проверка системы...$(NC)"
	@make check-python-version
	@which $(UV) > /dev/null && echo "$(GREEN)UV установлен$(NC)" || echo "$(YELLOW)UV не установлен$(NC)"
	@if [ -d ".venv" ] && [ -f ".venv/bin/python" ]; then \
		. .venv/bin/activate && python -c "import appraiser_photo_bot; print(f'$(GREEN)Пакет найден: {appraiser_photo_bot.__version__}$(NC)')" 2>/dev/null || echo "$(RED)Пакет не установлен в venv$(NC)"; \
	fi
	@which appraiser-photo-bot > /dev/null && echo "$(GREEN)CLI команда доступна$(NC)" || echo "$(YELLOW)CLI команда не найдена$(NC)"

.DEFAULT_GOAL := help