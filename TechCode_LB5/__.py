import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Type, ClassVar

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QLabel, QDialog,
    QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox,
    QMessageBox
)

DATA_FILE = "cars.json"


# ---------- Модель ----------
@dataclass
class Car:
    brand: str
    model: str
    price: float
    TYPE: ClassVar[str] = "AbstractCar"  # НЕ сериализуется

    @staticmethod
    def from_dict(d: dict) -> "Car":
        return Car(
            brand=d.get("brand", ""),
            model=d.get("model", ""),
            price=float(d.get("price", 0.0)),
            TYPE=int(d.get("TYPE", 0)),
        )


def load_Cars() -> List[Car]:
    if not os.path.exists(DATA_FILE):
        # Демо-данные при первом запуске
        demo = [
            Car("Rifle", "AK-47", 25000, 30, 600),
            Car("Pistol", "PM", 12000, 8, 120),
            Car("Knife", "Bayonet", 1500, 0, 0),
        ]
        save_Cars(demo)
        return demo
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Car.from_dict(x) for x in data]
    except Exception:
        QMessageBox.warning(None, "Load error", "Не удалось прочитать Cars.json. Будет создан новый файл.")
        save_Cars([])
        return []


def save_Cars(items: List[Car]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([asdict(x) for x in items], f, ensure_ascii=False, indent=2)


# ---------- Диалог добавления/редактирования ----------
class AddEditDialog(QDialog):
    def __init__(self, parent=None, Car: Car | None = None):
        super().__init__(parent)
        self.setWindowTitle("AddForm")

        self.cmb_class = QComboBox()
        self.cmb_class.addItems(["Rifle", "Pistol", "Knife", "SMG", "Shotgun", "Sniper"])
        self.cmb_class.setEditable(True)  # можно вписать свой класс

        self.le_name = QLineEdit()
        self.sb_price = QDoubleSpinBox()
        self.sb_price.setRange(0, 10_000_000)
        self.sb_price.setDecimals(2)
        self.sb_price.setSingleStep(100)

        self.sb_capacity = QSpinBox()
        self.sb_capacity.setRange(0, 10_000)

        self.sb_rapidity = QSpinBox()
        self.sb_rapidity.setRange(0, 10_000)

        form = QFormLayout()
        form.addRow("Class:", self.cmb_class)
        form.addRow("Name:", self.le_name)
        form.addRow("Price:", self.sb_price)
        form.addRow("Capacity:", self.sb_capacity)
        form.addRow("Rapidity:", self.sb_rapidity)

        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Cancel")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btns)

        if Car:
            self.cmb_class.setCurrentText(Car.wclass)
            self.le_name.setText(Car.name)
            self.sb_price.setValue(Car.price)
            self.sb_capacity.setValue(Car.capacity)
            self.sb_rapidity.setValue(Car.rapidity)

    def get_Car(self) -> Car:
        return Car(
            wclass=self.cmb_class.currentText().strip(),
            name=self.le_name.text().strip(),
            price=float(self.sb_price.value()),
            capacity=int(self.sb_capacity.value()),
            rapidity=int(self.sb_rapidity.value()),
        )

    def accept(self):
        # Простая валидация
        if not self.le_name.text().strip():
            QMessageBox.warning(self, "Validation", "Поле Name обязательно.")
            return
        if not self.cmb_class.currentText().strip():
            QMessageBox.warning(self, "Validation", "Поле Class обязательно.")
            return
        super().accept()


# ---------- Главное окно ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cars")
        self.resize(520, 380)

        self.items: List[Car] = load_Cars()

        central = QWidget()
        self.setCentralWidget(central)

        # Левая колонка с кнопками
        self.btn_add = QPushButton("add")
        self.btn_edit = QPushButton("edit")
        self.btn_del = QPushButton("delete")
        self.btn_edit.setEnabled(False)
        self.btn_del.setEnabled(False)

        left = QVBoxLayout()
        left.addWidget(self.btn_add)
        left.addWidget(self.btn_edit)
        left.addWidget(self.btn_del)
        left.addStretch(1)

        # Список
        self.listw = QListWidget()
        self.listw.itemSelectionChanged.connect(self._on_select_changed)
        self.listw.itemDoubleClicked.connect(self._on_edit_double)

        # Низ: Total
        self.lbl_total_caption = QLabel("TotalPrice:")
        self.lbl_total_value = QLabel("0")
        total_row = QHBoxLayout()
        total_row.addWidget(self.lbl_total_caption)
        total_row.addStretch(1)
        total_row.addWidget(self.lbl_total_value)

        right = QVBoxLayout()
        right.addWidget(self.listw)
        right.addLayout(total_row)

        main = QHBoxLayout(central)
        main.addLayout(left)
        main.addLayout(right, stretch=1)

        # Сигналы
        self.btn_add.clicked.connect(self._on_add)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_del.clicked.connect(self._on_delete)

        self.refresh_ui()

    # --- UI helpers ---
    def refresh_ui(self):
        self.listw.clear()
        for w in self.items:
            if isinstance(w.price, float) and w.price.is_integer():
                txt = f"{w.name} - {int(w.price)}"
            else:
                txt = f"{w.name} - {w.price:.2f}"

            it = QListWidgetItem(txt)
            it.setData(Qt.UserRole, w)  # храним объект в item
            self.listw.addItem(it)
        self._update_total()

    def _update_total(self):
        total = sum(w.price for w in self.items)
        # формат как на скрине (без копеек, если целое)
        self.lbl_total_value.setText(str(int(total) if float(total).is_integer() else round(total, 2)))

    def _current_index(self) -> int:
        row = self.listw.currentRow()
        return row if 0 <= row < len(self.items) else -1

    # --- Slots ---
    def _on_select_changed(self):
        has = self._current_index() != -1
        self.btn_edit.setEnabled(has)
        self.btn_del.setEnabled(has)

    def _on_add(self):
        dlg = AddEditDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self.items.append(dlg.get_Car())
            save_Cars(self.items)
            self.refresh_ui()

    def _on_edit(self):
        idx = self._current_index()
        if idx == -1:
            return
        dlg = AddEditDialog(self, self.items[idx])
        if dlg.exec_() == QDialog.Accepted:
            self.items[idx] = dlg.get_Car()
            save_Cars(self.items)
            self.refresh_ui()

    def _on_edit_double(self, _item: QListWidgetItem):
        self._on_edit()

    def _on_delete(self):
        idx = self._current_index()
        if idx == -1:
            return
        if QMessageBox.question(self, "Confirm", "Удалить выбранный объект?") == QMessageBox.Yes:
            self.items.pop(idx)
            save_Cars(self.items)
            self.refresh_ui()


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
