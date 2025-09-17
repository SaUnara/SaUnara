import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QFileDialog, QProgressBar,
                             QLabel, QMessageBox, QLineEdit, QHBoxLayout, QTreeWidgetItem)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QTreeWidget
import sys
import shutil
import subprocess
import platform


class FolderDetection():
    def __init__(self, folder_path):
        super().__init__()
        self.path = folder_path
        self.foldername = os.path.basename(folder_path)
        self.LMTest = os.path.normpath(os.path.join(folder_path, 'LM-Test'))

    def detectfolder(self):
        #   先检测是否有LM-Test文件夹
        print(f'Current detecting Folder Name: {self.foldername}')
        print(f'Current detecting Folder Path: {self.path}')
        if not os.path.isdir(self.LMTest):
            print('No LM-Test inside')
            return

        print(f'[Found] LM-Test inside {self.foldername}')

        # 遍历 LM-Test 内部的文件夹和文件
        for root, dirs, files in os.walk(self.LMTest):
            rel_path = os.path.relpath(root, self.path)
            print(f" [DIR] {rel_path}")
            for d in dirs:
                print(f"   [SUBDIR] {os.path.join(rel_path, d)}")
            for f in files:
                print(f"   [FILE] {os.path.join(rel_path, f)}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.base_folder = ''
        self.setWindowTitle('Detect Multiple Folders')
        self.setGeometry(100, 100, 800, 600)

        self.button_select = QPushButton("Select Folder(parents)")
        self.button_select.clicked.connect(self.select_parent_folder)

        self.label_selected_folder = QLabel("No folder selected.")
        self.label_selected_folder.setStyleSheet("color: gray")

        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel('Standby')
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.start_input = QLineEdit()
        self.start_input.setPlaceholderText('Start SN number')

        self.end_input = QLineEdit()
        self.end_input.setPlaceholderText('End SN number')

        self.button_start = QPushButton('Start Detection')
        self.button_start.clicked.connect(self.start_detection)

        # Start SN 输入行
        start_label = QLabel('Start SN number: ')
        start_layout = QHBoxLayout()
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_input)

        # End SN 输入行
        end_label = QLabel('End SN number: ')
        end_layout = QHBoxLayout()
        end_layout.addWidget(end_label)
        end_layout.addWidget(self.end_input)

        # 添加 TreeWidget
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(['Folder', ''])  # 第三个列用于按钮
        self.tree_widget.setColumnWidth(0, 250)

        layout = QVBoxLayout()
        layout.addWidget(self.button_select)
        layout.addWidget(self.label_selected_folder)
        layout.addLayout(start_layout)
        layout.addLayout(end_layout)
        #   layout.addWidget(self.start_input)
        #   layout.addWidget(self.end_input)
        layout.addWidget(self.button_start)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("Results:"))
        layout.addWidget(self.tree_widget)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def select_parent_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Folders')
        if not folder:
            QMessageBox.information(self, 'Info', 'No Folder Selected')
            return
        else:
            self.base_folder = folder.replace("\\", '/')
            self.label_selected_folder.setText(f'Folder Selected: {self.base_folder}')
            QMessageBox.information(self, 'Info', f'Folder Selected:\n{self.base_folder}')

    def start_detection(self):
        if not self.base_folder:
            QMessageBox.warning(self, 'Warning', 'Please select a parent folder first.')
            return

        start_num = int(self.start_input.text())
        end_num = int(self.end_input.text())

        # 构造目标编号列表：['SN0000', 'SN0001', ..., 'SN0500']
        target_names = [f"SN{str(i).zfill(4)}" for i in range(start_num, end_num + 1)]

        # 获取该目录下所有子文件夹
        all_subfolders = [
            os.path.join(self.base_folder, name).replace('\\', '/')
            for name in os.listdir(self.base_folder)
            if os.path.isdir(os.path.join(self.base_folder, name)) and name.startswith("SN") and name in target_names
        ]

        if not all_subfolders:
            QMessageBox.information(self, 'Info', 'No matching folders found.')
            return

        lmtest_count = 0  # 剩余LM-Test文件夹计数器

        original_stdout = sys.stdout
        movement_name = f'LM-Detection_{start_num}-{end_num}.txt'
        movement_path = os.path.join(r'D:/', movement_name)
        # 防止文件重名
        counter = 1
        while os.path.exists(movement_path):
            movement_path = os.path.join(r'D:/', f'LM-Detection_{start_num}-{end_num}_{counter}.txt')
            counter += 1

        with open(movement_path, 'w', encoding="utf-8") as file:
            sys.stdout = file
            for i, folder in enumerate(all_subfolders):
                folder_name = os.path.basename(folder)
                detector = FolderDetection(folder)
                if os.path.isdir(detector.LMTest):  # 如果存在 LM-Test
                    lmtest_count += 1
                detector.detectfolder()

        sys.stdout = original_stdout
        QMessageBox.information(self, 'Done', f'Detection finished.\n{lmtest_count} Folders Found.\nResults saved to {movement_path}')

        return


        # original_stdout = sys.stdout
        # movement_name = f'Movement_{start_num}-{end_num}.txt'
        # movement_path = os.path.join(r'D:/', movement_name)
        # # 防止文件重名
        # counter = 1
        # while os.path.exists(movement_path):
        #     movement_path = os.path.join(r'D:/', f'Movement_{self.start_num}-{self.end_num}_{counter}.txt')
        #     counter += 1
        #
        # with open(movement_path, 'w', encoding="utf-8") as file:
        #     sys.stdout = file
        #     for i, folder in enumerate(all_subfolders):
        #         folder_name = os.path.basename(folder)





if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()