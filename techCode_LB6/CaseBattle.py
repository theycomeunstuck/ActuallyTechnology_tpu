# case_battle.py
# Требуется: pip install PyQt5
import sys
import random
from dataclasses import dataclass
from typing import Tuple, List, Dict

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QPainter, QColor, QIcon, QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QMessageBox,
    QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem, QFrame, QSizePolicy, QSpacerItem
)


@dataclass
class Rarity:
    key: str                   # машинное имя
    name_ru: str               # отображаемое русское имя
    weight: int                # вероятность (вес)
    color: Tuple[int, int, int]
    value_range: Tuple[int, int]
    items: List[Tuple[str, str]]  # (название, эмодзи/икон-текст)


class CaseBattleWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # --- Параметры игры ---
        self.start_balance = 1600
        self.case_price = 105

        # Настройка редкостей и пул предметов
        self.rarities: List[Rarity] = [
            Rarity(
                key="common",
                name_ru="обычное",
                weight=70,
                color=(176, 190, 197),           # серо-голубой
                value_range=(15, 80),
                items=[
                    ("Ржавый нож", "🗡️"),
                    ("Старая кепка", "🧢"),
                    ("Пластиковый браслет", "📿"),
                    ("Потёртая карта", "🗺️"),
                    ("Сломанный компас", "🧭"),
                ],
            ),
            Rarity(
                key="rare",
                name_ru="редкое",
                weight=15,
                color=(100, 181, 246),           # синий
                value_range=(60, 200),
                items=[
                    ("Амулет удачи", "🧿"),
                    ("Полированный клинок", "🔪"),
                    ("Сапоги разведчика", "👢"),
                    ("Медальон героя", "🎖️"),
                    ("Редкая монета", "🪙"),
                ],
            ),
            Rarity(
                key="epic",
                name_ru="эпическое",
                weight=5,
                color=(186, 104, 200),           # фиолетовый
                value_range=(100, 500),
                items=[
                    ("Посох бурь", "🪄"),
                    ("Маска тени", "🎭"),
                    ("Клинок бури", "⚡"),
                    ("Кольцо мудреца", "💍"),
                    ("Книга тайн", "📜"),
                ],
            ),
            Rarity(
                key="legendary",
                name_ru="легендарное",
                weight=1,
                color=(255, 193, 7),             # золотистый
                value_range=(400, 1200),
                items=[
                    ("Драконий меч", "🐉"),
                    ("Корона королей", "👑"),
                    ("Талисман феникса", "🔥"),
                    ("Звёздный артефакт", "✨"),
                    ("Клинок рассвета", "🌅"),
                ],
            ),
        ]

        # --- Состояние ---
        self.balance = self.start_balance

        self.init_ui()

    # ---------- UI ----------
    def init_ui(self):
        self.setWindowTitle("Case Battle — симулятор кейсов (Русская версия)")
        self.setMinimumSize(900, 520)

        central = QWidget(self)
        self.setCentralWidget(central)

        # Основной горизонтальный лейаут: слева управление, справа лог
        root = QHBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # Левая панель (управление)
        left = QVBoxLayout()
        left.setSpacing(12)

        # Заголовок / баланс
        title = QLabel("Case Battle")
        tfont = QFont()
        tfont.setPointSize(18)
        tfont.setBold(True)
        title.setFont(tfont)
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.balance_label = QLabel(self._balance_text())
        bfont = QFont()
        bfont.setPointSize(16)
        bfont.setBold(True)
        self.balance_label.setFont(bfont)
        self.balance_label.setStyleSheet("color: #2e7d32;")  # зелёный

        price_label = QLabel(f"Цена кейса: {self.case_price} монет")
        price_label.setStyleSheet("color: #455a64;")

        note = QLabel("Примечание: стоимость предмета автоматически\nзачисляется на баланс.")
        note.setStyleSheet("color: #607d8b;")
        note.setWordWrap(True)

        # Кнопки
        self.open_btn = QPushButton("Открыть кейс")
        self.open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn.setMinimumHeight(40)
        self.open_btn.clicked.connect(self.on_open_case)

        exit_btn = QPushButton("Выйти")
        exit_btn.setCursor(Qt.PointingHandCursor)
        exit_btn.setMinimumHeight(36)
        exit_btn.clicked.connect(self.close)

        # Разделитель (тонкая линия)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #B0BEC5;")

        left.addWidget(title)
        left.addWidget(self.balance_label)
        left.addWidget(price_label)
        left.addWidget(line)
        left.addWidget(self.open_btn)
        left.addWidget(exit_btn)
        left.addSpacing(8)
        left.addWidget(note)
        left.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Правая панель (лог)
        right = QVBoxLayout()
        right.setSpacing(8)

        log_title = QLabel("Вы выиграли:")
        lfont = QFont()
        lfont.setPointSize(12)
        lfont.setBold(True)
        log_title.setFont(lfont)

        self.log_list = QListWidget()
        self.log_list.setIconSize(QSize(48, 48))
        self.log_list.setAlternatingRowColors(True)
        self.log_list.setStyleSheet("""
            QListWidget {
                background: #FAFAFA;
                border: 1px solid #CFD8DC;
            }
            QListWidget::item {
                padding: 8px;
            }
        """)

        right.addWidget(log_title)
        right.addWidget(self.log_list)

        root.addLayout(left, 1)
        root.addLayout(right, 2)

        self._update_open_button_state()

    # ---------- Игровая логика ----------
    def on_open_case(self):
        if self.balance < self.case_price:
            self._not_enough_money()
            return

        # Списываем стоимость кейса
        self.balance -= self.case_price

        # Выбор редкости по весам
        rarity = self._choose_rarity()
        item_name, emoji = random.choice(rarity.items)
        value = random.randint(*rarity.value_range)

        # Автозачисление стоимости предмета на баланс
        self.balance += value

        # Обновление интерфейса
        self.balance_label.setText(self._balance_text())
        self._update_open_button_state()

        # Добавляем запись в лог
        icon = QIcon(self._make_item_icon(rarity.color, emoji))
        text = f"{item_name} — {rarity.name_ru.capitalize()} | Стоимость: {value} монет"
        self._append_log(icon, text)

    def _append_log(self, icon: QIcon, text: str):
        item = QListWidgetItem(icon, text)
        self.log_list.addItem(item)
        self.log_list.scrollToBottom()

    def _choose_rarity(self) -> Rarity:
        weights = [r.weight for r in self.rarities]
        return random.choices(self.rarities, weights=weights, k=1)[0]

    # ---------- Иконки ----------
    def _make_item_icon(self, rgb: Tuple[int, int, int], text: str) -> QPixmap:
        """Простая иконка: цветной скруглённый прямоугольник + эмодзи/текст."""
        w, h = 48, 48
        pix = QPixmap(w, h)
        pix.fill(Qt.transparent)

        r, g, b = rgb
        color = QColor(r, g, b)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Фон
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 10, 10)

        # Текст (эмодзи)
        painter.setPen(Qt.black)
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(0, 0, w, h, Qt.AlignCenter, text)
        painter.end()
        return pix

    # ---------- Вспомогательные ----------
    def _balance_text(self) -> str:
        return f"Баланс: {self.balance} монет"

    def _not_enough_money(self):
        QMessageBox.warning(
            self,
            "Недостаточно средств",
            "Недостаточно средств для открытия кейса.\n"
            "Попробуйте позже или завершите игру.",
            QMessageBox.Ok
        )

    def _update_open_button_state(self):
        can_open = self.balance >= self.case_price
        self.open_btn.setEnabled(can_open)
        if not can_open:
            self.open_btn.setToolTip("Недостаточно средств для открытия кейса")
        else:
            self.open_btn.setToolTip("Открыть один кейс за указанную цену")


def main():
    app = QApplication(sys.argv)
    # Небольшая светлая тема
    app.setStyleSheet("""
        QWidget { font-family: Segoe UI, Arial; font-size: 11pt; }
        QPushButton {
            background-color: #1976D2; color: white; border: none; padding: 8px 14px;
            border-radius: 8px;
        }
        QPushButton:hover { background-color: #1565C0; }
        QPushButton:disabled { background-color: #90A4AE; color: #ECEFF1; }
        QLabel { color: #263238; }
        QMainWindow { background: #FFFFFF; }
    """)
    win = CaseBattleWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
