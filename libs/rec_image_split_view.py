import sys
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QMessageBox, QDialog
from PyQt5.QtGui import QPixmap, QPen, QColor
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtWidgets import QGraphicsItem
from .ui.rec_split_label_dialog import Ui_Dialog

class ScaleBar(QGraphicsItem):
    def __init__(self, length, height=40, tick_interval=10, font_size=10):
        super().__init__()
        self.length = length
        self.height = height
        self.tick_interval = tick_interval
        self.font_size = font_size

    def boundingRect(self):
        return QRectF(0, 0, self.length, self.height)

    def paint(self, painter, option, widget):
        painter.setPen(QPen(Qt.black))
        font = painter.font()
        font.setPointSize(self.font_size)
        painter.setFont(font)

        for i in range(int(self.length)):
            if i % self.tick_interval == 0:
                x = i
                painter.drawLine(x, self.height-10, x, self.height)
                painter.drawText(QPointF(x-5, self.height//2), str(round(i//self.tick_interval)))

class ImageWidget(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = None
        self.scale_bar = None
        self.vertical_lines = []  # 存储垂直线条的列表

    def load_image(self, image_path):
        pixmap = QPixmap(image_path)
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.scale_bar = ScaleBar(
            length=self.pixmap_item.boundingRect().width(), 
            tick_interval=self.pixmap_item.boundingRect().height())
        self.scene.addItem(self.scale_bar)
        self.center_image()

    def image_width(self):
        return self.pixmap_item.boundingRect().width()

    def split_positions(self):
        return [int(line.line().x1()) for line in self.vertical_lines]

    def center_image(self):
        if self.pixmap_item:
            x = (self.scene.width() - self.pixmap_item.boundingRect().width()) / 2
            y = (self.scene.height() - self.pixmap_item.boundingRect().height()) / 2
            self.pixmap_item.setPos(x, y)
            self.scale_bar.setPos(x, y - self.scale_bar.boundingRect().height())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.pixmap_item:
            pos = self.mapToScene(event.pos())
            x = pos.x() - self.pixmap_item.pos().x()
            min_distance = float('inf')
            closest_line = None
            for line in self.vertical_lines:
                line_x = line.line().x1()
                distance = abs(line_x - x)
                if distance < min_distance:
                    min_distance = distance
                    closest_line = line
            thresh = 10
            if event.modifiers() == Qt.ControlModifier:  # 判断是否按下Ctrl键
                if min_distance < thresh and closest_line:
                    self.scene.removeItem(closest_line)
                    self.vertical_lines.remove(closest_line)
                    self.scene.update()
            else:               
                if min_distance < thresh and closest_line:
                    self.scene.removeItem(closest_line)
                    self.vertical_lines.remove(closest_line)
                line = self.scene.addLine(x, 0, x, self.pixmap_item.boundingRect().height(),
                                        QPen(QColor(255, 0, 0)))                    
                self.vertical_lines.append(line)
                self.scene.update()
        super().mousePressEvent(event)


class RecImageSplitDialog(QDialog, Ui_Dialog):
    def __init__(self, image_file, label):
        super().__init__()
        self.setupUi(self) 
        screen = QApplication.primaryScreen()
        # 获取屏幕的尺寸（分辨率）
        screen_size = screen.size()
        # 计算对话框的宽度和高度，设置为屏幕尺寸的一半
        dialog_width = screen_size.width() * 2 // 3
        dialog_height = screen_size.height() *2 // 3
        # 设置对话框的固定大小
        self.setFixedSize(dialog_width, dialog_height)

        self.image_fille = image_file
        self.label = label
        self.textEdit.setText(label)
        self.imageWidget = ImageWidget()
        self.imageWidget.load_image(self.image_fille)
        self.imageLayout.addWidget(self.imageWidget)
        self.btnCancel.clicked.connect(self.reject)
        self.btnOK.clicked.connect(self.on_ok)

    def on_ok(self):
        self.positions = self.imageWidget.split_positions()
        self.texts = self.textEdit.toPlainText().split('\n')
        if len(self.positions) == 0:
            self.reject()
            return

        if len(self.texts) != len(self.positions) + 1:
            QMessageBox.warning(self.widget, '提示', '图像分片数量和文本行数不一致！')
            return

        self.accept()

    def get_data(self):
        return self.positions, self.texts

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RecImageSplitDialog('d:/data/english/hw-font-rendered/images/BantengStory/0.png', '')
    window.show()
    sys.exit(app.exec())
