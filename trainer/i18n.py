"""Small RU/EN catalog shared by UI labels and local bridge diagnostics."""
from __future__ import annotations

import re

LANGUAGES = {"en": "English", "ru": "Русский"}
_language = "en"

EN = {
    "Язык": "Language",
    "Папка Steam…": "Steam folder…",
    "Копии сохранений": "Save backups",
    "Журнал игры": "Game logs",
    "Игра не подключена": "Game not connected",
    "Запустить с модом": "Launch with mods",
    "Загрузи сохранение, чтобы включить читы.": "Load a save to enable cheats.",
    "Сбросить временные читы": "Reset temporary cheats",
    "Игра может записать читы в сохранение. Перед запуском создаётся резервная копия.\nЗакрытие окна сбрасывает текущие настройки за 4 секунды, но не откатывает сохранения.":
        "The game may save cheat effects. Saves are backed up before launch.\nClosing this window resets runtime settings within 4 seconds, but does not roll back saves.",
    "Выживание и способности": "Survival and abilities",
    "Бесконечная нить": "Infinite silk",
    "Бесконечная душа": "Infinite soul",
    "Урон и темп игры": "Damage and game pace",
    "Множитель урона": "Damage multiplier",
    "Скорость игры": "Game speed",
    "Применяй, когда игра не на паузе": "Apply while the game is unpaused",
    "Скорость движения": "Movement speed",
    "Бег и ходьба героя": "Hero running and walking speed",
    "Ресурсы": "Resources",
    "Добавляется к текущему количеству": "Added to your current balance",
    "Выбери SteamLibrary": "Choose SteamLibrary",
    "Локально на твоём Mac\nБез Windows и Wine": "Locally on your Mac\nNo Windows or Wine",
    "Нативная macOS · ": "Native macOS · ",
    "Неуязвимость": "Invincibility",
    "Игнорировать попадания": "Ignore incoming hits",
    "Бесконечное здоровье": "Infinite health",
    "Маски не расходуются": "Keep your health masks",
    "Ресурс для способностей не заканчивается": "Keep your ability resource full",
    "Бесконечные прыжки": "Infinite jumps",
    "Повторный прыжок в воздухе": "Jump again while in the air",
    "Бесконечные рывки": "Unlimited dashes",
    "Без задержки; способность должна быть открыта": "No cooldown; requires the unlocked ability",
    "Быстрая атака": "Fast attack",
    "Убирает задержку между ударами": "Remove the cooldown between attacks",
    "Проход сквозь стены": "Noclip",
    "Свободное перемещение; включай осторожно": "Move through walls; use with care",
    "Гвоздь": "Nail",
    "Игла": "Needle",
    "Добавить Geo": "Add Geo",
    "Добавить розарии": "Add rosaries",
    "Добавить осколки": "Add shell shards",
    "Осколки панциря": "Shell shards",
    "Добавить": "Add",
    "Применить": "Apply",
    "Запускаю…": "Launching…",
    "Подключено · можно включать читы": "Connected · cheats available",
    "Применяю…": "Applying…",
    "розариев": "rosaries",
    "Дождитесь завершения запуска игры.": "Wait for the game to finish launching.",
    "Бесконечные инструменты": "Infinite tools",
    "Использование без расхода": "Use tools without consuming charges",
    "Игра запущена · загрузи сохранение": "Game running · load a save",
    "Здоровье {health}/{maximum}   ·   {balance} {currency}   ·   урон {damage:g}×   ·   темп {speed:g}×":
        "Health {health}/{maximum}   ·   {balance} {currency}   ·   damage {damage:g}×   ·   speed {speed:g}×",
    "Игра перезапущена; настройки не переносились.": "Game restarted; previous settings were not carried over.",
    "Игра не найдена. Укажите папку SteamLibrary.": "Game not found. Select your SteamLibrary folder.",
    "Игра уже запущена. Закройте её перед запуском с модом.": "The game is already running. Close it before launching with mods.",
    "Связь прервалась. Результат последнего действия неизвестен.": "Connection lost. The result of the last action is unknown.",
    "Дождитесь подтверждения предыдущего действия.": "Wait for the previous action to be acknowledged.",
    "Запустите игру с модом.": "Launch the game with mods.",
    "Загрузите сохранение и дождитесь управления героем.": "Load a save and wait until you can control the hero.",
    "Нет подтверждения. Проверьте игру перед повторным действием.": "No acknowledgement. Check the game before trying again.",
    "Не удалось проверить резервную копию сохранения.": "Could not verify the save backup.",
    "DebugMod не загрузился. Проверьте журнал игры.": "DebugMod did not load. Check the game logs.",
    "Ожидание DebugMod": "Waiting for DebugMod",
    "Слишком много запросов: перезапустите игру.": "Too many requests: restart the game.",
    "Сеанс изменился. Повторите действие.": "The session changed. Try the action again.",
    "Сначала загрузите сохранение и дождитесь управления героем.": "First load a save and wait until you can control the hero.",
    "Неверное значение": "Invalid value",
    "Неизвестный переключатель": "Unknown toggle",
    "Недоступный переключатель": "Toggle unavailable",
    "Переключатель: 0 или 1": "Toggle value must be 0 or 1",
    "Скорость движения: от 0.5 до 3×": "Movement speed must be between 0.5 and 3×",
    "Инструменты доступны в Silksong": "Tools are available in Silksong only",
    "Урон: от 1 до 20×": "Damage must be between 1 and 20×",
    "Скорость: от 0.5 до 3×": "Speed must be between 0.5 and 3×",
    "Снимите игру с паузы для изменения скорости.": "Unpause the game before changing its speed.",
    "Количество: 1–100000": "Amount must be between 1 and 100000",
    "Количество: 1–10000": "Amount must be between 1 and 10000",
    "Неизвестная команда": "Unknown command",
}


def set_language(language: str) -> None:
    global _language
    _language = language if language in LANGUAGES else "en"


def get_language() -> str:
    return _language


def tr(message: str, **values) -> str:
    translated = EN.get(message, message) if _language == "en" else message
    # The existing bridge/client protocol stays language-neutral in structure.
    # Translate its one version-dependent diagnostic without changing that protocol.
    if _language == "en" and message.startswith("Установлена версия "):
        match = re.fullmatch(r"Установлена версия (.*); проверена (.*)\. Нужна проверка совместимости\.", message)
        if match:
            translated = f"Installed version {match[1]}; tested version {match[2]}. Compatibility needs to be verified."
    return translated.format(**values) if values else translated
