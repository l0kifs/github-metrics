# github-metrics

Асинхронная библиотека для сбора метрик GitHub с использованием GraphQL API.

## Описание

`github-metrics` - это Python библиотека для сбора метрик по Pull Request'ам из GitHub репозиториев. Библиотека использует GitHub GraphQL API для эффективного получения данных и полностью поддерживает асинхронность.

## Основные возможности

- **Асинхронный сбор метрик**: Полная поддержка async/await
- **GitHub GraphQL API**: Использование эффективного GraphQL API вместо REST
- **Фильтрация по времени**: Сбор метрик за указанный период времени
- **Фильтрация по ветке**: Возможность фильтровать PR по целевой ветке (main, develop и т.д.)
- **Детальная информация по PR**: 
  - Целевая ветка (base branch)
  - Количество изменений (additions + deletions)
  - Количество добавленных строк (additions)
  - Количество удалённых строк (deletions)
  - Время нахождения PR на ревью
  - Количество коммитов
  - Количество комментариев и review комментариев
  - Список пользователей, поставивших approve
  - Список пользователей, оставивших комментарии
  - Метки (labels) PR
  - Полное описание PR
- **Разделение по резолюции**: Merged vs Closed (не merged)
- **Исключение draft PR**: Draft PR не учитываются в метриках

## Технический стек

- **Python**: 3.12+
- **httpx**: Асинхронный HTTP клиент
- **loguru**: Структурированное логирование
- **pydantic**: Валидация данных и настройки
- **pydantic-settings**: Управление конфигурацией

## Установка

```bash
pip install github-metrics
```

Или для разработки:

```bash
git clone https://github.com/l0kifs/github-metrics.git
cd github-metrics
pip install -e .
```

## Конфигурация

Библиотека использует переменные окружения для конфигурации. Создайте файл `.env` или установите переменные окружения:

```bash
GITHUB_METRICS__GITHUB_TOKEN=your_github_personal_access_token
GITHUB_METRICS__GITHUB_API_URL=https://api.github.com/graphql  # опционально
GITHUB_METRICS__LOGGING_LEVEL=INFO  # опционально
```

### Получение GitHub Token

1. Перейдите в Settings → Developer settings → Personal access tokens
2. Создайте новый token с правами:
   - `repo` (полный доступ к приватным репозиториям) или
   - `public_repo` (доступ только к публичным репозиториям)

## Использование

### Базовый пример

```python
import asyncio
from datetime import UTC, datetime, timedelta
from github_metrics import MetricsCollector, get_settings

async def main():
    # Получение настроек (из переменных окружения)
    settings = get_settings()
    
    # Инициализация коллектора
    collector = MetricsCollector(settings)
    
    # Определение периода (например, последние 30 дней)
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=30)
    
    # Сбор метрик
    # Можно указать целевую ветку (base_branch) для фильтрации
    # Например: base_branch="main" или base_branch="develop"
    metrics = await collector.collect_pr_metrics(
        owner="octocat",
        repo="Hello-World",
        start_date=start_date,
        end_date=end_date,
        base_branch=None,  # None = все ветки
    )
    
    # Использование результатов
    print(f"Total PRs: {metrics.total_prs}")
    print(f"Merged PRs: {metrics.merged_prs}")
    print(f"Closed (not merged) PRs: {metrics.closed_prs}")
    
    for pr in metrics.pull_requests:
        print(f"PR #{pr.number}: {pr.title}")
        print(f"  Resolution: {pr.resolution}")
        print(f"  Changes: {pr.changes_count}")
        print(f"  Review time: {pr.review_time_hours:.2f} hours")
        print(f"  Approvers: {[u.login for u in pr.approvers]}")

if __name__ == "__main__":
    asyncio.run(main())
```

Для полного рабочего примера с детальным выводом и экспортом в JSON, см. `examples/example.py`.

### Работа с моделями данных

```python
from github_metrics.models import PRMetrics, PRResolution, RepositoryMetrics

# Metrics для репозитория содержит список всех PR
for pr in metrics.pull_requests:
    # Основная информация
    print(pr.number, pr.title, pr.url)
    print(f"Target branch: {pr.base_branch}")
    print(pr.author.login, pr.author.name)
    
    # Даты
    print(pr.created_at, pr.closed_at, pr.merged_at)
    
    # Резолюция
    if pr.resolution == PRResolution.MERGED:
        print("PR был смержен")
    else:
        print("PR был закрыт без мержа")
    
    # Метрики
    print(f"Изменений: {pr.changes_count}")
    print(f"Добавлено строк: {pr.additions_count}")
    print(f"Удалено строк: {pr.deletions_count}")
    print(f"Время на ревью: {pr.review_time_hours} часов")
    print(f"Коммитов: {pr.commits_count}")
    print(f"Комментариев: {pr.comments_count}")
    print(f"Review комментариев: {pr.review_comments_count}")
    
    # Участники
    print(f"Approvers: {[u.login for u in pr.approvers]}")
    print(f"Commenters: {[u.login for u in pr.commenters]}")
    
    # Дополнительная информация
    print(f"Labels: {pr.labels}")
    print(f"Description: {pr.description}")
```

## Модели данных

### `User`
Информация о пользователе GitHub:
- `login: str` - имя пользователя
- `name: Optional[str]` - отображаемое имя

### `PRMetrics`
Метрики для отдельного Pull Request:
- `number: int` - номер PR
- `title: str` - заголовок PR
- `url: str` - URL PR
- `base_branch: str` - целевая ветка PR
- `author: User` - автор PR
- `created_at: datetime` - дата создания
- `closed_at: datetime` - дата закрытия
- `merged_at: Optional[datetime]` - дата мержа (если был)
- `resolution: PRResolution` - финальная резолюция
- `changes_count: int` - количество изменений (additions + deletions)
- `additions_count: int` - количество добавленных строк
- `deletions_count: int` - количество удалённых строк
- `review_time_hours: float` - время на ревью (часы)
- `commits_count: int` - количество коммитов
- `review_comments_count: int` - количество review комментариев
- `comments_count: int` - количество обычных комментариев
- `approvers: list[User]` - пользователи, поставившие approve
- `commenters: list[User]` - пользователи, оставившие комментарии
- `labels: list[str]` - метки PR
- `description: str` - полное описание PR

### `RepositoryMetrics`
Агрегированные метрики для репозитория:
- `repository: str` - имя репозитория (owner/repo)
- `period_start: datetime` - начало периода
- `period_end: datetime` - конец периода
- `pull_requests: list[PRMetrics]` - список метрик по PR
- `total_prs: int` - общее количество PR (property)
- `merged_prs: int` - количество смерженных PR (property)
- `closed_prs: int` - количество закрытых без мержа PR (property)

### `PRResolution`
Enum финальной резолюции PR:
- `MERGED` - PR был смержен
- `CLOSED_NOT_MERGED` - PR был закрыт без мержа

## Разработка

### Установка зависимостей для разработки

```bash
pip install -e ".[dev]"
# или
pip install mypy pytest ruff pytest-asyncio
```

### Запуск тестов

```bash
pytest tests/ -v
```

### Линтинг и форматирование

```bash
# Проверка кода
ruff check src/ tests/

# Форматирование
ruff format src/ tests/

# Проверка типов
mypy src/
```

## Лицензия

MIT License - см. файл [LICENSE](LICENSE)

## Авторы

- l0kifs - [l0kifs91@gmail.com](mailto:l0kifs91@gmail.com)

## Ссылки

- [GitHub Repository](https://github.com/l0kifs/github-metrics)
- [Issue Tracker](https://github.com/l0kifs/github-metrics/issues)
- [GitHub GraphQL API Documentation](https://docs.github.com/en/graphql)