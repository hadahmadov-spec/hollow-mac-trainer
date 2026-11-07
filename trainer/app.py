from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QThread, Signal, QLockFile
from PySide6.QtGui import QColor, QPainter, QFont, QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QCheckBox, QDoubleSpinBox, QSpinBox, QScrollArea, QFrame, QFileDialog, QComboBox)

from trainer.client import Client, GAMES, SUPPORT, atomic_json, launch
from trainer.i18n import tr, set_language, get_language, LANGUAGES


class Switch(QCheckBox):
    def __init__(self, label):
        super().__init__()
        self.setAccessibleName(label)
        self.setFixedSize(52, 30)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        color = "#f39a39" if self.isChecked() else "#464b53"
        painter.setOpacity(1 if self.isEnabled() else .45)
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(2, 5, 46, 22, 11, 11)
        painter.setBrush(QColor("#181b20" if self.isChecked() else "#e1e3e7"))
        painter.drawEllipse(29 if self.isChecked() else 5, 8, 16, 16)
        if self.hasFocus():
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QColor("#f8c185"))
            painter.drawRoundedRect(0, 2, 51, 27, 12, 12)

    def hitButton(self, pos):
        return self.rect().contains(pos)


class Launcher(QThread):
    done = Signal(object, str)
    def __init__(self, game, library):
        super().__init__()
        self.game, self.library = game, library
    def run(self):
        try:
            self.done.emit(launch(self.game, self.library), "")
        except Exception as error:
            self.done.emit(None, str(error))


STYLE = """
QMainWindow, QWidget {background:#181b20; color:#edf0f4; font-size:14px;}
QWidget#sidebar {background:#111419;}
QLabel#brand {font-size:18px; font-weight:650; color:#f2a451;}
QLabel#title {font-size:29px; font-weight:650;}
QLabel#muted {color:#adb6c2; font-size:12px;}
QLabel#section {color:#f4b776; font-size:13px; font-weight:600;}
QLabel#status {color:#c0c9d5;}
QLabel#error {color:#ffbe9c; font-size:12px;}
QPushButton {background:#292e37; border:1px solid #3b424e; border-radius:7px; padding:8px 13px;}
QPushButton:hover {background:#363d48;}
QPushButton:pressed {background:#454e5d;}
QPushButton:focus {border-color:#f7bf82;}
QPushButton:disabled {color:#68717d; background:#20252c; border-color:#303640;}
QPushButton#primary {background:#f39a39; color:#171a1f; font-weight:650; border-color:#f39a39; padding:11px 16px;}
QPushButton#primary:hover {background:#ffb15b;}
QPushButton#primary:disabled {background:#61482e; color:#b3a18c; border-color:#61482e;}
QPushButton#game {text-align:left; padding:13px 11px; border:0; background:transparent;}
QPushButton#game:checked {background:#2b3039; color:#ffc17d;}
QComboBox, QDoubleSpinBox, QSpinBox {background:#11151a; border:1px solid #4b5563; border-radius:5px; padding:7px; min-width:86px;}
QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {border-color:#f7bf82;}
QScrollArea {border:0;}
QFrame#separator {background:#323943; max-height:1px;}
QScrollBar:vertical {background:#1b2027; width:9px;}
QScrollBar::handle:vertical {background:#525c69; min-height:30px; border-radius:4px;}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {height:0;}
"""


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hollow · Mac Trainer")
        self.resize(920, 760)
        self.setMinimumSize(820, 660)
        self.clients = {key: Client(key) for key in GAMES}
        self.game = "knight"
        self.launcher = None
        self.processes = {}
        self.library = ""
        try:
            self.preferences = json.loads((SUPPORT / "preferences.json").read_text())
            if not isinstance(self.preferences, dict):
                self.preferences = {}
        except (OSError, ValueError):
            self.preferences = {}
        self.library = self.preferences.get("library", "")
        set_language(self.preferences.get("language", "en"))
        self.build_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(350)
        self.refresh()

    def build_ui(self):
        container = QWidget()
        self.setCentralWidget(container)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        side = QWidget(objectName="sidebar")
        side.setFixedWidth(190)
        sidebar = QVBoxLayout(side)
        sidebar.setContentsMargins(18, 28, 18, 22)
        sidebar.setSpacing(12)
        sidebar.addWidget(QLabel("Hollow\nMac Trainer", objectName="brand"))
        sidebar.addSpacing(24)
        self.game_buttons = {}
        for key, info in GAMES.items():
            button = QPushButton(info["title"], objectName="game")
            button.setCheckable(True)
            button.setChecked(key == self.game)
            button.clicked.connect(lambda checked=False, k=key: self.select_game(k))
            sidebar.addWidget(button)
            self.game_buttons[key] = button
        sidebar.addStretch()
        sidebar.addWidget(QLabel(tr("Язык"), objectName="muted"))
        self.language_combo = QComboBox()
        self.language_combo.setAccessibleName(tr("Язык"))
        for code, label in LANGUAGES.items():
            self.language_combo.addItem(label, code)
        self.language_combo.setCurrentIndex(self.language_combo.findData(get_language()))
        self.language_combo.currentIndexChanged.connect(lambda: self.change_language(self.language_combo.currentData()))
        sidebar.addWidget(self.language_combo)
        self.library_button = QPushButton(tr("Папка Steam…"))
        self.library_button.clicked.connect(self.choose_library)
        sidebar.addWidget(self.library_button)
        backups = QPushButton(tr("Копии сохранений"))
        backups.clicked.connect(lambda: self.open_folder(SUPPORT / "backups"))
        sidebar.addWidget(backups)
        logs = QPushButton(tr("Журнал игры"))
        logs.clicked.connect(lambda: self.open_folder(self.clients[self.game].folder))
        sidebar.addWidget(logs)
        sidebar.addSpacing(12)
        sidebar.addWidget(QLabel(tr("Локально на твоём Mac\nБез Windows и Wine"), objectName="muted"))
        layout.addWidget(side)
        main = QWidget()
        column = QVBoxLayout(main)
        column.setContentsMargins(28, 25, 28, 20)
        column.setSpacing(12)
        self.title = QLabel(objectName="title")
        column.addWidget(self.title)
        self.version = QLabel(objectName="muted")
        column.addWidget(self.version)
        status_row = QHBoxLayout()
        self.status = QLabel(tr("Игра не подключена"), objectName="status")
        status_row.addWidget(self.status, 1)
        self.start = QPushButton(tr("Запустить с модом"), objectName="primary")
        self.start.clicked.connect(self.start_game)
        status_row.addWidget(self.start)
        column.addLayout(status_row)
        self.stats = QLabel(tr("Загрузи сохранение, чтобы включить читы."), objectName="muted")
        column.addWidget(self.stats)
        self.error = QLabel(objectName="error")
        self.error.setWordWrap(True)
        column.addWidget(self.error)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.body = QWidget()
        self.rows = QVBoxLayout(self.body)
        self.rows.setContentsMargins(0, 2, 8, 0)
        self.rows.setSpacing(0)
        scroll.setWidget(self.body)
        column.addWidget(scroll, 1)
        footer = QHBoxLayout()
        self.reset = QPushButton(tr("Сбросить временные читы"))
        self.reset.clicked.connect(lambda: self.command("reset"))
        footer.addWidget(self.reset)
        footer.addStretch()
        self.busy = QLabel("", objectName="muted")
        footer.addWidget(self.busy)
        column.addLayout(footer)
        note = QLabel(tr("Игра может записать читы в сохранение. Перед запуском создаётся резервная копия.\nЗакрытие окна сбрасывает текущие настройки за 4 секунды, но не откатывает сохранения."), objectName="muted")
        note.setWordWrap(True)
        column.addWidget(note)
        layout.addWidget(main, 1)
        self.build_rows()

    def change_language(self, language):
        if language == get_language():
            return
        preferences = {**self.preferences, "language": language}
        try:
            atomic_json(SUPPORT / "preferences.json", preferences)
        except OSError as error:
            self.error.setText(str(error))
            self.language_combo.blockSignals(True)
            self.language_combo.setCurrentIndex(self.language_combo.findData(get_language()))
            self.language_combo.blockSignals(False)
            return
        values = {key: widget.value() for key, widget in self.numbers.items()}
        self.preferences = preferences
        set_language(language)
        self.build_ui()
        for key, value in values.items():
            self.numbers[key].setValue(value)
        self.language_combo.setFocus()
        self.refresh()

    def select_game(self, game):
        self.game = game
        for key, button in self.game_buttons.items():
            button.setChecked(key == game)
        self.build_rows()
        self.refresh()

    def build_rows(self):
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.controls = []
        self.switches = {}
        self.numbers = {}
        self.title.setText(GAMES[self.game]["title"])
        self.version.setText(tr("Нативная macOS · ") + GAMES[self.game]["version"])
        self.section(tr("Выживание и способности"))
        resource = tr("Бесконечная нить") if self.game == "silksong" else tr("Бесконечная душа")
        rows = [("invincible", tr("Неуязвимость"), tr("Игнорировать попадания")),
                ("health", tr("Бесконечное здоровье"), tr("Маски не расходуются")),
                ("resource", resource, tr("Ресурс для способностей не заканчивается")),
                ("jump", tr("Бесконечные прыжки"), tr("Повторный прыжок в воздухе"))]
        rows += [("dash", tr("Бесконечные рывки"), tr("Без задержки; способность должна быть открыта")),
                 ("fastAttack", tr("Быстрая атака"), tr("Убирает задержку между ударами"))]
        if self.game == "silksong": rows.append(("tools", tr("Бесконечные инструменты"), tr("Использование без расхода")))
        rows.append(("noclip", tr("Проход сквозь стены"), tr("Свободное перемещение; включай осторожно")))
        for key, title, description in rows:
            switch = Switch(title)
            switch.clicked.connect(lambda checked, k=key: self.command(k, int(checked)))
            self.switches[key] = switch
            self.add_row(title, description, switch)
        self.section(tr("Урон и темп игры"))
        self.numeric("damage", tr("Множитель урона"), tr("Гвоздь") if self.game == "knight" else tr("Игла"), 1, 20, 1, .5, "×")
        self.numeric("speed", tr("Скорость игры"), tr("Применяй, когда игра не на паузе"), .5, 3, 1, .1, "×")
        self.numeric("move", tr("Скорость движения"), tr("Бег и ходьба героя"), .5, 3, 1, .1, "×")
        self.section(tr("Ресурсы"))
        self.numeric("currency", tr("Добавить Geo") if self.game == "knight" else tr("Добавить розарии"), tr("Добавляется к текущему количеству"), 1, 100000, 1000, 100, "", integer=True)
        if self.game == "silksong":
            self.numeric("shards", tr("Добавить осколки"), tr("Осколки панциря"), 1, 10000, 100, 10, "", integer=True)
        self.rows.addStretch()

    def section(self, text):
        label = QLabel(text, objectName="section")
        label.setContentsMargins(0, 18, 0, 9)
        self.rows.addWidget(label)

    def add_row(self, title, description, control):
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 10, 0, 10)
        text = QVBoxLayout()
        text.setSpacing(3)
        text.addWidget(QLabel(title))
        description_label = QLabel(description, objectName="muted")
        description_label.setWordWrap(True)
        text.addWidget(description_label)
        row.addLayout(text, 1)
        row.addWidget(control)
        self.rows.addWidget(widget)
        self.rows.addWidget(QFrame(objectName="separator"))
        self.controls.append(control)

    def numeric(self, key, title, description, low, high, default, step, suffix, integer=False):
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        value = QSpinBox() if integer else QDoubleSpinBox()
        value.setRange(low, high)
        value.setSingleStep(step)
        value.setValue(default)
        value.setSuffix(suffix)
        value.setAccessibleName(title)
        if not integer: value.setDecimals(1)
        value.setFixedWidth(105)
        button = QPushButton(tr("Добавить") if integer else tr("Применить"))
        button.clicked.connect(lambda: self.command(key, value.value()))
        layout.addWidget(value)
        layout.addWidget(button)
        self.numbers[key] = value
        self.add_row(title, description, panel)

    def command(self, operation, value=0):
        try:
            self.clients[self.game].send(operation, value)
        except Exception as error:
            self.clients[self.game].error = str(error)
        self.refresh()

    def refresh(self):
        states = {game: client.poll() for game, client in self.clients.items()}
        client = self.clients[self.game]
        state = states[self.game]
        ready = bool(state and state.get("ready"))
        pending = client.pending is not None
        for control in self.controls: control.setEnabled(ready and not pending)
        self.reset.setEnabled(bool(state) and not pending)
        running = self.launcher is not None and self.launcher.isRunning()
        self.start.setEnabled(not state and not running)
        self.start.setText(tr("Запускаю…") if running else tr("Запустить с модом"))
        self.status.setText(tr("Подключено · можно включать читы") if ready else tr("Игра запущена · загрузи сохранение") if state else tr("Игра не подключена"))
        self.status.setStyleSheet("color:#b9d6bf" if ready else "")
        self.busy.setText(tr("Применяю…") if pending else "")
        self.error.setText(tr(client.error or (state.get("error", "") if state else "")))
        if state:
            currency = tr("розариев") if self.game == "silksong" else "Geo"
            self.stats.setText(tr("Здоровье {health}/{maximum}   ·   {balance} {currency}   ·   урон {damage:g}×   ·   темп {speed:g}×", health=state.get('health', 0), maximum=state.get('maxHealth', 0), balance=state.get('currency', 0), currency=currency, damage=state.get('damage', 1), speed=state.get('speed', 1)))
        else:
            self.stats.setText(tr("Загрузи сохранение, чтобы включить читы."))
        for key, switch in self.switches.items():
            if not pending:
                switch.setChecked(bool(state and state.get("healthLock" if key == "health" else key)))

    def start_game(self):
        self.launcher = Launcher(self.game, self.library)
        self.launcher.done.connect(self.launch_done)
        self.launcher.start()
        self.refresh()

    def launch_done(self, process, error):
        game = self.launcher.game
        if error: self.clients[game].error = error
        else: self.processes[game] = process
        self.refresh()

    def choose_library(self):
        folder = QFileDialog.getExistingDirectory(self, tr("Выбери SteamLibrary"), self.library or "/Volumes")
        if folder:
            self.library = folder
            self.preferences["library"] = folder
            atomic_json(SUPPORT / "preferences.json", self.preferences)

    def open_folder(self, path):
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def closeEvent(self, event):
        if self.launcher and self.launcher.isRunning():
            self.error.setText(tr("Дождитесь завершения запуска игры."))
            event.ignore()
            return
        self.timer.stop()
        for client in self.clients.values(): client.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Hollow Mac Trainer")
    app.setStyle("Fusion")
    app.setFont(QFont(".AppleSystemUIFont", 13))
    app.setStyleSheet(STYLE)
    SUPPORT.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = QLockFile(str(SUPPORT / "app.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        return 0
    window = Window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
