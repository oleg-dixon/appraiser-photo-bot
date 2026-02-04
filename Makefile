.PHONY: help install install-dev setup-env run clean test lint format type-check check-all \
        build publish install-package uninstall docker-build docker-run docker-clean

# Цвета для вывода
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Переменные
PYTHON := python3
UV := uv
PACKAGE_NAME := appraiser-photo-bot
ENV_FILE := .env
ENV_EXAMPLE := .env.example

help: ## Показать это сообщение
	@echo "$(YELLOW)Доступные команды:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

venv-create: ## Создать виртуальное окружение
	@echo "$(YELLOW)Создаю виртуальное окружение...$(NC)"
	@$(UV) venv .venv
	@echo "$(GREEN)Виртуальное окружение создано в .venv$(NC)"

venv-help: ## Показать справку по активации виртуального окружения
	@echo "$(YELLOW)Активация виртуального окружения:$(NC)"
	@echo ""
	@echo "$(GREEN)Linux/Mac:$(NC)"
	@echo "  source .venv/bin/activate"
	@echo ""
	@echo "$(GREEN)Windows (PowerShell):$(NC)"
	@echo "  .venv\\Scripts\\Activate.ps1"
	@echo ""
	@echo "$(GREEN)Windows (CMD):$(NC)"
	@echo "  .venv\\Scripts\\activate.bat"
	@echo ""
	@echo "$(YELLOW)Проверка:$(NC)"
	@echo "  which python    # должен показывать .venv/bin/python"
	@echo "  python --version"

venv: venv-create venv-help ## Создать виртуальное окружение и показать справку

install: ## Установить зависимости через uv (использует setup.py)
	@echo "$(YELLOW)Устанавливаю зависимости...$(NC)"
	@$(UV) pip install -e .

install-dev: ## Установить зависимости для разработки
	@echo "$(YELLOW)Устанавливаю зависимости для разработки...$(NC)"
	@$(UV) pip install -e ".[dev]"

setup-env: ## Настроить файл окружения
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

clean: ## Очистить временные файлы и кэш
	@echo "$(YELLOW)Очищаю временные файлы...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name ".coverage" -delete
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

test: ## Запустить тесты
	@echo "$(YELLOW)Запускаю тесты...$(NC)"
	@$(UV) run pytest tests/ -v --cov=appraiser_photo_bot --cov-report=term-missing

lint: ## Проверить код с помощью ruff
	@echo "$(YELLOW)Проверяю код с помощью ruff...$(NC)"
	@$(UV) run ruff check .

lint-fix: ## Исправить автоматически исправимые проблемы с помощью ruff
	@echo "$(YELLOW)Исправляю автоматически исправимые проблемы...$(NC)"
	@$(UV) run ruff check . --fix

lint-all: ## Проверить и пофиксить код с помощью ruff
	@echo "$(YELLOW)Проверяю и исправляю код...$(NC)"
	@$(UV) run ruff check . --output-format=full

format: ## Форматировать код с помощью ruff
	@echo "$(YELLOW)Форматирую код...$(NC)"
	@$(UV) run ruff format .

check-style: ## Проверить стиль кода с помощью ruff
	@echo "$(YELLOW)Проверяю стиль кода...$(NC)"
	@$(UV) run ruff format . --check

type-check: ## Проверить типы с помощью mypy
	@echo "$(YELLOW)Проверяю типы...$(NC)"
	@$(UV) run mypy appraiser_photo_bot/ document_creators/

check-all: lint check-style type-check test ## Выполнить все проверки

quick-check: lint-fix format ## Быстрая проверка и исправление кода

build: ## Собрать пакет
	@echo "$(YELLOW)Собираю пакет...$(NC)"
	@$(UV) build
	@echo "$(GREEN)Пакет собран в директории dist/$(NC)"

install-package: build ## Установить локально собранный пакет
	@echo "$(YELLOW)Устанавливаю локальный пакет...$(NC)"
	@$(UV) pip install dist/$(PACKAGE_NAME)-*.tar.gz

uninstall: ## Удалить пакет
	@echo "$(YELLOW)Удаляю пакет...$(NC)"
	@$(UV) pip uninstall $(PACKAGE_NAME) -y || true

docker-build: ## Собрать Docker образ (требует Dockerfile)
	@echo "$(YELLOW)Собираю Docker образ...$(NC)"
	@docker build -t $(PACKAGE_NAME) .

docker-run: ## Запустить в Docker (требует Dockerfile)
	@echo "$(YELLOW)Запускаю в Docker...$(NC)"
	@docker run --env-file $(ENV_FILE) --rm $(PACKAGE_NAME)

docker-clean: ## Очистить Docker образы
	@echo "$(YELLOW)Очищаю Docker образы...$(NC)"
	@docker rmi $(PACKAGE_NAME) 2>/dev/null || true

docker-down: ## Остановить Docker Compose
	@echo "$(YELLOW)Останавливаю Docker Compose...$(NC)"
	@docker-compose down

docker-logs: ## Показать логи контейнера
	@echo "$(YELLOW)Логи контейнера:$(NC)"
	@docker-compose logs -f bot

docker-shell: ## Зайти в shell контейнера
	@echo "$(YELLOW)Открываю shell в контейнере...$(NC)"
	@docker-compose exec bot sh

docker-test: ## Запустить тесты в Docker
	@echo "$(YELLOW)Запускаю тесты в Docker...$(NC)"
	@docker-compose run --rm bot make test

update-deps: ## Обновить зависимости
	@echo "$(YELLOW)Обновляю зависимости...$(NC)"
	@echo "$(YELLOW)Эта команда не работает с setup.py, используйте pip-compile вручную$(NC)"

init: setup-env install-dev ## Инициализировать проект (первый запуск)
	@echo "$(GREEN)Проект инициализирован!$(NC)"
	@echo "$(YELLOW)Не забудьте добавить BOT_TOKEN в файл .env$(NC)"

venv: ## Создать виртуальное окружение с помощью uv
	@echo "$(YELLOW)Создаю виртуальное окружение...$(NC)"
	@$(UV) venv .venv
	@echo "$(GREEN)Виртуальное окружение создано в .venv$(NC)"
	@echo "$(YELLOW)Активируйте его командой:$(NC)"
	@echo "  source .venv/bin/activate  # Linux/Mac"
	@echo "  .venv\\Scripts\\activate     # Windows"

check-env: ## Проверить наличие файла .env
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "$(RED)Ошибка: файл $(ENV_FILE) не найден!$(NC)"; \
		echo "Создайте его командой: make setup-env"; \
		exit 1; \
	else \
		echo "$(GREEN)Файл $(ENV_FILE) найден.$(NC)"; \
	fi

bot: check-env run ## Запустить бота с проверкой окружения

ci: check-all ## Запустить все проверки для CI/CD

version: ## Показать версию пакета
	@$(PYTHON) -c "from appraiser_photo_bot import __version__; print(f'Версия: {__version__}')"

check: ## Проверить установлен ли пакет и доступны ли команды
	@echo "$(YELLOW)Проверка системы...$(NC)"
	@which $(UV) > /dev/null || echo "$(RED)UV не установлен!$(NC)"
	@$(PYTHON) -c "import appraiser_photo_bot; print(f'$(GREEN)Пакет найден: {appraiser_photo_bot.__version__}$(NC)')" 2>/dev/null || echo "$(RED)Пакет не установлен$(NC)"
	@which appraiser-photo-bot > /dev/null && echo "$(GREEN)CLI команда доступна$(NC)" || echo "$(YELLOW)CLI команда не найдена (запустите make install)$(NC)"

.PHONY: help
.DEFAULT_GOAL := help
