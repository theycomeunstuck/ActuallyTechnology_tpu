import sys
from PyQt5.QtWidgets import QApplication, QWidget

# Создаём приложение
app = QApplication(sys.argv)

# Создаём окно
window = QWidget()
window.setWindowTitle("Моё первое окно на PyQt")
window.resize(400, 300)  # размер окна
window.show()  # показать окно

# Запуск приложения (главный цикл)
sys.exit(app.exec_())
