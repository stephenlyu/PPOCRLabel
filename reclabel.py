import sys
import os
import shutil
__dir__ = os.path.dirname(__file__)
sys.path.append(os.path.join(__dir__, ""))

from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5 import QtCore
from libs.ui.rec_label_window import Ui_MainWindow  # 导入生成的 UI 类

cache_dir = '.cache'
max_samples = 20000
max_history = 10

class History:
    def __init__(self):
        self.history_file = os.path.join(cache_dir, 'history')
        self.history = []
        if os.path.exists(self.history_file):            
            with open(self.history_file, encoding='utf-8') as f:
                self.history = f.read().split('\n')
    
    def _flush(self):
        if not os.path.exists(self.history_file):
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, 'w', encoding='utf-8') as w:
            w.write('\n'.join(self.history))        

    def add(self, s):
        if s in self.history:
            self.history.remove(s)            
        self.history.insert(0, s)
        if len(self.history) > max_history:
            self.history = self.history[:max_history]
        self._flush()
    
    def clear(self):
        self.history = []
        self._flush()

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)  # 调用生成的 UI 类的 setupUi 方法

        self.action_O.triggered.connect(self.onOpen)
        self.action_O.setShortcut('Ctrl+O')
        self.action_S.triggered.connect(self.onSave)
        self.action_S.setShortcut('Ctrl+S')
        self.textEdit.textChanged.connect(self.on_text_changed)
        self.action_C.triggered.connect(self.onClose)
        self.action_C.setEnabled(False)        
        self.action_E.triggered.connect(self.onExport)
        self.action_E.setEnabled(False)
        self.action_D.triggered.connect(self.onDelete)
        self.action_D.setEnabled(False)

        self.history = History()
        self.label_file = None
        self.image_root = None
        self.labels = []
        self.current_label_index = None

        self.listModel = None
        self.build_history_menu()
        self.actionClearHistory.triggered.connect(self.clear_history)

    def clear_history(self):
        self.history.clear()
        self.build_history_menu()

    def update_history(self):
        for i, his in enumerate(self.history.history):
            if his == self.label_file:
                self.his_actions[i].setChecked(True)
            else:
                self.his_actions[i].setChecked(False)

    def build_history_menu(self):
        self.menuHistory.clear()
        self.his_actions = []

        def handler(his):
            def on_trigger():
                if his == self.label_file:
                    return
                self.load_labels(his)
            return on_trigger

        for his in self.history.history:
            action =  QtWidgets.QAction(self)
            action.setText(his)
            action.setCheckable(True)
            action.triggered.connect(handler(his))
            self.menuHistory.addAction(action)
            self.his_actions.append(action)
        if self.history.history:
            self.menuHistory.addSeparator()
        self.menuHistory.addAction(self.actionClearHistory)
        self.update_history()

    def set_label_changed(self, v):
        self.action_S.setEnabled(v)

    def deduce_image_root(self, image_file):
        if os.path.exists(image_file):
            return ''
        root = os.path.abspath(os.path.dirname(self.label_file))
        while True:
            file_path = os.path.join(root, image_file)
            if os.path.exists(file_path):
                return root
            if root == '/' or len(root) < 4:
                break
            root = os.path.abspath(os.path.join(root, '..'))
        return None

    def calculate_max_text_width(self):
        """
        计算 QListView 中最长文本的宽度
        :return: 最长文本的宽度（像素）
        """
        # 获取 QListView 的字体
        font = self.listView.font()

        # 创建 QFontMetrics 对象
        font_metrics = QtGui.QFontMetrics(font)

        # 初始化最大宽度
        max_width = 0

        # 遍历模型中的所有项
        for _, label in self.labels:
            # 获取文本
            # 计算文本的宽度
            text_width = font_metrics.width(label)
            # 更新最大宽度
            if text_width > max_width:
                max_width = text_width

        return int(max_width*0.7)

    def render_labels(self):
        self.reset_state()
        self.listModel = QtGui.QStandardItemModel()
        for image, _ in self.labels:
            standard_item = QtGui.QStandardItem(image)
            self.listModel.appendRow(standard_item)

        self.listView.setModel(self.listModel)
        self.listView.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.listView.selectionModel().selectionChanged.connect(self.on_selection_changed)

        max_width = self.calculate_max_text_width()
        if max_width > self.width() // 2:
            max_width = self.width() // 2
        if max_width < 100:
            max_width = 100
        self.listView.setMinimumWidth(max_width)
        self.statusBar().showMessage('样本数量%d' % len(self.labels))

        if self.labels:
            self.current_label_index = 0
            index = self.listModel.index(self.current_label_index, 0)  # 第 3 项的索引
            self.listView.selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.Select)

    def load_image(self, file_path):
        """
        加载图像文件并显示在 QLabel 中
        :param file_path: 图像文件路径
        """
        # 使用 QPixmap 加载图像
        pixmap = QtGui.QPixmap(file_path)
        
        if pixmap.isNull():
            # 如果加载失败，显示错误信息
            self.lblImage.setText("无法加载图像")
        else:
            # 将 QPixmap 设置到 QLabel 中
            self.lblImage.setPixmap(pixmap)

        self.lblImgRatio.setText('图像长宽比: %.02f' % (pixmap.width()/pixmap.height()))

    def on_selection_changed(self, selected, deselected):
        selected_indexes = self.listView.selectionModel().selectedIndexes()        
        self.current_label_index = selected_indexes[0].row()
        image, label = self.labels[selected_indexes[0].row()]
        self.load_image(os.path.join(self.image_root, image))
        self.textEdit.setText(label)
        self.lblLabelLen.setText('标签字符数: %d' % len(label))        

    def on_text_changed(self):
        image, text = self.labels[self.current_label_index] 
        text = self.textEdit.text()
        self.lblLabelLen.setText('标签字符数: %d' % len(text))
        self.labels[self.current_label_index] = (image, text)
        self.set_label_changed(True)

    def reset_state(self):
        self.lblImgRatio.setText('')
        self.lblLabelLen.setText('')
        self.lblImage.setPixmap(QtGui.QPixmap())
        self.lblImage.setText('暂无图像')
        self.textEdit.setText('')
        if self.listModel:
            self.listModel.clear()

        self.statusBar().showMessage('')
        self.action_C.setEnabled(False)      
        self.action_E.setEnabled(False)      
        self.action_D.setEnabled(False)
        self.set_label_changed(False)
        self.update_history()

    def project_file(self):
        return self.label_file + '.prj'

    def load_labels(self, label_file):
        print('加载%s...' % label_file)
        self.label_file = label_file
        self.image_root = None

        prj_file = self.project_file()
        if not os.path.exists(prj_file):
            prj_file = label_file

        with open(prj_file, encoding='utf-8') as f:
            self.labels = []
            for line in f:
                line = line.rstrip('\r\n')
                if not line:
                    continue
                parts = line.split('\t')
                if self.image_root is None:
                    self.image_root = self.deduce_image_root(parts[0])
                    if self.image_root is None:
                        print('无法推断出图像所在目录')
                        QtWidgets.QMessageBox.warning(self, "警告", "无法推断出图像所在目录")    
                        self.label_file = None
                        break
                self.labels.append((parts[0], ' '.join(parts[1:])))
                if len(self.labels) >= max_samples:
                    QtWidgets.QMessageBox.warning(self, "警告", 
                        "最多支持%d个样本，请将标注文件按%d数量切分。" % (max_samples, max_samples))    
                    break        
        self.render_labels()
        self.set_label_changed(False)
        self.history.add(self.label_file)
        self.build_history_menu()
        self.action_C.setEnabled(True)        
        self.action_E.setEnabled(True)  
        if len(self.labels) > 0:      
            self.action_D.setEnabled(True)

    def load_prev_open_dir(self):
        file = os.path.join(cache_dir, 'prev_open_dir')
        if not os.path.exists(file):
            return ''
        with open(file, 'r', encoding='utf-8') as f:
            return f.read()

    def save_prev_open_dir(self, dir):
        os.makedirs(cache_dir, exist_ok=True)
        file = os.path.join(cache_dir, 'prev_open_dir')
        with open(file, 'w', encoding='utf-8') as f:
            f.write(dir)
        
    def onOpen(self): 
        if self.label_file is not None:       
            self.onClose()
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,                  # 父窗口
            "打开识别GT文件",        # 对话框标题
            self.load_prev_open_dir(),                   # 初始目录（空字符串表示当前目录）
            "文本文件 (*.txt)"    # 文件过滤器
        )

        # 如果用户选择了文件
        if file_name:
            self.save_prev_open_dir(os.path.dirname(file_name))
            if file_name != self.label_file:
                self.load_labels(file_name)

    def onClose(self):
        if self.action_S.isEnabled():
            reply = QtWidgets.QMessageBox.question(self, "确认", "内容未保存，保存吗？",
                                  QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                self.onSave()
        self.label_file = None
        self.reset_state()

    def onSave(self):
        if not self.labels:
            return
        prj_file = self.project_file()
        tmp_file = prj_file + '.tmp'
        with open(tmp_file, 'w', encoding='utf-8') as f:
            for image, label in self.labels:
                f.write('%s\t%s\n' % (image, label))
        if os.path.exists(prj_file):
            os.unlink(prj_file)
        os.rename(tmp_file, prj_file)
        self.set_label_changed(False)

    def onExport(self):
        if self.label_file is None:
            return
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,                  # 父窗口
            "保存文件",        # 对话框标题
            os.path.dirname(self.label_file),                   # 初始目录（空字符串表示当前目录）
            "文本文件 (*.txt)"    # 文件过滤器
        )
        if file_name:
            self.onSave()
            shutil.copyfile(self.project_file(), file_name)
            QtWidgets.QMessageBox.information(self, "信息", "文件导出成功。")    

    def onDelete(self):
        if self.current_label_index >=0 and self.current_label_index < len(self.labels):
            self.labels.pop(self.current_label_index)
            if self.listModel:
                self.listModel.takeRow(self.current_label_index)
            if self.current_label_index >= len(self.labels):
                self.current_label_index = len(self.labels) - 1
            if self.current_label_index >= 0:
                index = self.listModel.index(self.current_label_index, 0)  # 第 3 项的索引
                self.listView.selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.Select)
            else:
                self.action_D.setEnabled(False)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)  # 创建应用程序对象
    window = MainWindow()  # 创建主窗口对象
    window.showMaximized()  # 显示主窗口
    sys.exit(app.exec_())  # 进入主事件循环
