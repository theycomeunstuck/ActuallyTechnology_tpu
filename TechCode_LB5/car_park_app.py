# -*- coding: utf-8 -*-
"""
ДВА ОКНА:
1) Главное окно "Автопарк": список, кнопки Добавить/Редактировать/Удалить, итоговая сумма.
2) Окно Б (диалог) добавления/редактирования: динамические "особые параметры" по классу.

Русские подписи, валидация, понятные комментарии.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QListView, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFormLayout, QLineEdit, QTextEdit, QMessageBox,
    QAbstractItemView, QStatusBar, QStyleFactory, QDialog, QDialogButtonBox,
    QComboBox, QSpinBox, QCheckBox
)

# ---- справочник особых полей по классам ------------------------------------
# ключ: имя поля (в хранилище), значение: (читаемая метка, тип_виджета, kwargs для виджета)
# тип_виджета: "spin" (целое), "check" (булево), "text" (строка)
CLASS_FIELDS: Dict[str, List[Tuple[str, str, str, Dict]]] = {
    "Sedan":      [("trunkVolume", "Объём багажника, л", "spin", {"minimum": 100, "maximum": 1200, "singleStep": 10})],
    "SUV":        [("clearance", "Клиренс, мм", "spin", {"minimum": 120, "maximum": 400, "singleStep": 5})],
    "Hatchback":  [("doorsCount", "Количество дверей", "spin", {"minimum": 2, "maximum": 5, "singleStep": 1})],
    "Coupe":      [("sportMode", "Спортивный режим", "check", {})],
    "luxurySUV":  [("soundSystem", "Аудиосистема", "text", {})],
    "compactSUV": [("climateControl", "Климат-контроль", "check", {})],
    # "Другое" — без специальных полей
}

# ---- модель данных ----------------------------------------------------------

@dataclass
class Car:
    """Сущность 'класс автомобиля'."""
    car_class: str           # Sedan / SUV / ...
    name: str                # модель
    price: float             # цена
    description: str         # общее текстовое описание
    extra: Dict[str, object] = field(default_factory=dict)  # особые характеристики по классу


class CarStore:
    """Память для одного автопарка (главного окна)."""
    def __init__(self, cars: Optional[List[Car]] = None) -> None:
        self.cars: List[Car] = list(cars or [])

    def add(self, car: Car) -> int:
        self.cars.append(car)
        return len(self.cars) - 1

    def update(self, idx: int, car: Car) -> None:
        self.cars[idx] = car

    def remove(self, idx: int) -> None:
        del self.cars[idx]

    def total_price(self) -> float:
        return float(sum(c.price for c in self.cars))


# ---- окно Б: диалог редактирования -----------------------------------------

class EditCarDialog(QDialog):
    """
    Окно Б — добавление/редактирование.
    Динамически строит блок "Особые параметры" в зависимости от выбранного класса.
    """
    def __init__(self, parent=None, car: Optional[Car] = None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setMinimumWidth(520)
        self._result_car: Optional[Car] = None

        # --- верхние поля (общие) ---
        self.cb_class = QComboBox()
        # Список классов (включая "Другое")
        all_classes = list(CLASS_FIELDS.keys()) + ["Другое"]
        self.cb_class.addItems(all_classes)

        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("Например: Toyota Camry")

        self.ed_price = QLineEdit()
        dv = QDoubleValidator(0.0, 1_000_000_000.0, 2, self.ed_price)
        dv.setNotation(QDoubleValidator.StandardNotation)
        self.ed_price.setValidator(dv)
        self.ed_price.setPlaceholderText("32999.99")

        self.ed_desc = QTextEdit()
        self.ed_desc.setPlaceholderText("Общее описание: мощность, пакет, цвет и т.п.")

        # --- форма ---
        form = QFormLayout()
        form.addRow("Класс:", self.cb_class)
        form.addRow("Название:", self.ed_name)
        form.addRow("Цена:", self.ed_price)
        form.addRow("Описание:", self.ed_desc)

        # --- динамическая секция 'Особые параметры' ---
        self.special_caption = QLabel("Особые параметры класса")
        self.special_caption.setStyleSheet("font-weight:600; margin-top:8px;")
        self.special_container = QWidget()          # сюда будем пересобирать поля
        self.special_layout = QFormLayout(self.special_container)
        self.special_layout.setContentsMargins(0, 0, 0, 0)
        self._extra_widgets: Dict[str, QWidget] = {}  # key -> widget

        # --- кнопки ---
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._try_accept)
        btns.rejected.connect(self.reject)

        # --- корневой layout ---
        root = QVBoxLayout(self)
        title = QLabel("Редактирование класса" if car else "Добавление класса")
        title.setStyleSheet("font-weight:700; font-size:16px;")
        root.addWidget(title)
        root.addLayout(form)
        root.addWidget(self.special_caption)
        root.addWidget(self.special_container)
        root.addWidget(btns)

        # --- события ---
        self.cb_class.currentTextChanged.connect(self._rebuild_special_fields)

        # --- если редактируем существующий объект ---
        if car:
            # если класса нет в списке — выберем "Другое"
            if car.car_class in all_classes:
                self.cb_class.setCurrentText(car.car_class)
            else:
                self.cb_class.setCurrentText("Другое")
            self.ed_name.setText(car.name)
            self.ed_price.setText(f"{float(car.price):.2f}")
            self.ed_desc.setPlainText(car.description)
            # сначала построим поля, затем заполним значения
            self._rebuild_special_fields()
            for key, w in self._extra_widgets.items():
                if key in car.extra:
                    val = car.extra[key]
                    if isinstance(w, QSpinBox):
                        try:
                            w.setValue(int(val))
                        except Exception:
                            pass
                    elif isinstance(w, QCheckBox):
                        w.setChecked(bool(val))
                    elif isinstance(w, QLineEdit):
                        w.setText(str(val))
        else:
            self.cb_class.setCurrentText("Sedan")
            self._rebuild_special_fields()

        self.setWindowTitle("Редактирование класса" if car else "Добавление класса")

    # ---------- служебные: построение/чтение блока 'Особые' ------------------

    def _clear_special(self) -> None:
        """Очистить контейнер особых полей."""
        while self.special_layout.count():
            item = self.special_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._extra_widgets.clear()

    def _rebuild_special_fields(self) -> None:
        """Пересобрать поля 'Особые параметры' для выбранного класса."""
        self._clear_special()
        cls = self.cb_class.currentText()
        fields = CLASS_FIELDS.get(cls, [])
        if not fields:
            # Для "Другое" просто покажем подсказку
            note = QLabel("Нет специальных параметров для выбранного класса.")
            note.setStyleSheet("color: #666;")
            self.special_layout.addRow("", note)
            return

        for key, label, kind, kwargs in fields:
            if kind == "spin":
                w = QSpinBox()
                # применяем параметры, если указаны
                for k, v in kwargs.items():
                    getattr(w, f"set{k[0].upper()+k[1:]}")(v)
                self.special_layout.addRow(label + ":", w)
            elif kind == "check":
                w = QCheckBox(label)
                self.special_layout.addRow("", w)
            elif kind == "text":
                w = QLineEdit()
                w.setPlaceholderText(label)
                self.special_layout.addRow(label + ":", w)
            else:
                continue
            self._extra_widgets[key] = w

    def _read_extras(self) -> Dict[str, object]:
        """Считать значения из виджетов особых полей."""
        extra: Dict[str, object] = {}
        for key, w in self._extra_widgets.items():
            if isinstance(w, QSpinBox):
                extra[key] = int(w.value())
            elif isinstance(w, QCheckBox):
                extra[key] = bool(w.isChecked())
            elif isinstance(w, QLineEdit):
                extra[key] = w.text().strip()
        return extra

    # ---------- валидация и завершение ---------------------------------------

    def _try_accept(self) -> None:
        """Проверить и сформировать Car; при успехе — accept()."""
        car_class = self.cb_class.currentText().strip()
        name = self.ed_name.text().strip()
        price_text = self.ed_price.text().replace(",", ".").strip()
        description = self.ed_desc.toPlainText().strip()

        if not car_class:
            QMessageBox.information(self, "Проверка", "Поле «Класс» не должно быть пустым.")
            return
        if not name:
            QMessageBox.information(self, "Проверка", "Поле «Название» не должно быть пустым.")
            self.ed_name.setFocus(); return
        if not price_text:
            QMessageBox.information(self, "Проверка", "Заполните «Цена».")
            self.ed_price.setFocus(); return

        try:
            price = float(price_text)
        except ValueError:
            QMessageBox.warning(self, "Проверка", "Цена должна быть числом (например 12345.67).")
            self.ed_price.setFocus(); return
        if price < 0:
            QMessageBox.warning(self, "Проверка", "Цена должна быть неотрицательной.")
            self.ed_price.setFocus(); return

        extra = self._read_extras()
        self._result_car = Car(
            car_class=car_class,
            name=name,
            price=price,
            description=description,
            extra=extra
        )
        self.accept()

    def result_car(self) -> Optional[Car]:
        """Получить результат после успешного OK (иначе None)."""
        return self._result_car


# ---- главное окно -----------------------------------------------------------

class CarParkWindow(QMainWindow):
    """Главное окно автопарка: список, кнопки, итоговая сумма."""
    def __init__(self, title: str, initial: Optional[List[Car]] = None) -> None:
        super().__init__()
        self.setWindowTitle(title)
        self.resize(780, 520)

        self.store = CarStore(initial)
        self.model = QStandardItemModel(self)

        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.list_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_view.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.btn_add = QPushButton("Добавить")
        self.btn_edit = QPushButton("Редактировать")
        self.btn_del = QPushButton("Удалить")

        caption = QLabel("Список классов автомобилей")
        caption.setStyleSheet("font-weight:600;")

        self.lbl_total_text = QLabel("Итоговая стоимость автопарка:")
        self.lbl_total_val = QLabel("0.00")
        self.lbl_total_val.setStyleSheet("font-weight:700;")

        center = QWidget()
        lay = QVBoxLayout(center)
        lay.addWidget(caption)
        lay.addWidget(self.list_view, stretch=1)

        btns = QHBoxLayout()
        btns.addWidget(self.btn_add)
        btns.addWidget(self.btn_edit)
        btns.addWidget(self.btn_del)
        btns.addStretch(1)
        lay.addLayout(btns)

        total = QHBoxLayout()
        total.addWidget(self.lbl_total_text)
        total.addSpacing(10)
        total.addWidget(self.lbl_total_val)
        total.addStretch(1)
        lay.addLayout(total)

        self.setCentralWidget(center)
        self.setStatusBar(QStatusBar())

        self.btn_add.clicked.connect(self.on_add)
        self.btn_edit.clicked.connect(self.on_edit)
        self.btn_del.clicked.connect(self.on_delete)

        self.refresh_list()

    # ---- утилиты -------------------------------------------------------------

    def _extra_summary(self, car: Car) -> str:
        """Короткая строка с особыми параметрами для отображения в списке."""
        cls = car.car_class
        fields = CLASS_FIELDS.get(cls, [])
        parts: List[str] = []
        for key, label, kind, _ in fields:
            if key not in car.extra:
                continue
            val = car.extra[key]
            # красивые единицы измерения
            if key == "trunkVolume":
                parts.append(f"багажник {val} л")
            elif key == "clearance":
                parts.append(f"клиренс {val} мм")
            elif key == "doorsCount":
                parts.append(f"{val} двери")
            elif key == "sportMode":
                parts.append("спорт-режим" + (" ✓" if val else " ✗"))
            elif key == "climateControl":
                parts.append("климат-контроль" + (" ✓" if val else " ✗"))
            elif key == "soundSystem":
                parts.append(f"аудио: {val}")
            else:
                parts.append(f"{label.lower()}: {val}")
        return ", ".join(parts)

    def _format_item_text(self, car: Car) -> str:
        extra = self._extra_summary(car)
        tail = f" — {extra}" if extra else ""
        return f"{car.car_class}: {car.name} — {car.price:.2f}{tail}"

    def refresh_list(self, select_row: Optional[int] = None) -> None:
        self.model.clear()
        for car in self.store.cars:
            it = QStandardItem(self._format_item_text(car))
            it.setEditable(False)
            it.setData(car, Qt.UserRole)
            self.model.appendRow(it)

        if select_row is not None and 0 <= select_row < self.model.rowCount():
            self.list_view.setCurrentIndex(self.model.index(select_row, 0))
        else:
            self.list_view.clearSelection()

        self.lbl_total_val.setText(f"{self.store.total_price():.2f}")

    def current_row(self) -> int:
        idx = self.list_view.currentIndex()
        return idx.row() if idx.isValid() else -1

    # ---- действия ------------------------------------------------------------

    def on_add(self) -> None:
        dlg = EditCarDialog(self, car=None)
        if dlg.exec_() == QDialog.Accepted:
            car = dlg.result_car()
            if car:
                row = self.store.add(car)
                self.refresh_list(select_row=row)
                self.statusBar().showMessage("Добавлено", 2500)

    def on_edit(self) -> None:
        row = self.current_row()
        if row < 0:
            QMessageBox.information(self, "Редактирование", "Сначала выберите элемент.")
            return
        dlg = EditCarDialog(self, car=self.store.cars[row])
        if dlg.exec_() == QDialog.Accepted:
            upd = dlg.result_car()
            if upd:
                self.store.update(row, upd)
                self.refresh_list(select_row=row)
                self.statusBar().showMessage("Изменения сохранены", 2500)

    def on_delete(self) -> None:
        row = self.current_row()
        if row < 0:
            QMessageBox.information(self, "Удаление", "Сначала выберите элемент.")
            return
        car = self.store.cars[row]
        if QMessageBox.question(self, "Удаление",
                                f"Удалить «{car.car_class}: {car.name}»?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            self.store.remove(row)
            new_sel = min(row, len(self.store.cars) - 1) if self.store.cars else None
            self.refresh_list(select_row=new_sel)
            self.statusBar().showMessage("Удалено", 2500)


# ---- запуск -----------------------------------------------------------------

def demo_data() -> List[Car]:
    return [
        Car("Sedan", "Toyota Camry", 32990.0, "2.5 л, 181 л.с.",
            extra={"trunkVolume": 480}),
        Car("SUV", "Hyundai Tucson", 40990.0, "Полный привод",
            extra={"clearance": 200}),
        Car("Hatchback", "VW Golf", 27990.0, "Экономичный",
            extra={"doorsCount": 5}),
        Car("Coupe", "BMW 430i", 55990.0, "Sport package",
            extra={"sportMode": True}),
        Car("luxurySUV", "Lexus RX", 71990.0, "Premium",
            extra={"soundSystem": "Mark Levinson"}),
        Car("compactSUV", "Kia Seltos", 28990.0, "City pack",
            extra={"climateControl": True}),
    ]


if __name__ == "__main__":
    import sys
    QApplication.setStyle(QStyleFactory.create("Fusion"))
    app = QApplication(sys.argv)
    w = CarParkWindow("Автопарк", demo_data())
    w.show()
    sys.exit(app.exec_())
