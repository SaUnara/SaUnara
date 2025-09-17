import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QFileDialog, QProgressBar,
                             QLabel, QMessageBox, QLineEdit, QHBoxLayout, QTreeWidgetItem)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QTreeWidget
import sys
import shutil
import subprocess
import platform
import hashlib
import time


class DetectFolders:
    def __init__(self, folder_path):
        self.path = folder_path
        self.foldername = os.path.basename(folder_path)
        # self.LMTest = os.path.join(folder_path, 'LM-Test').replace('\\', r'/')
        self.LMTest = os.path.normpath(os.path.join(folder_path, 'LM-Test'))

    def log_time(self, msg):
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def is_accessible(self, path):
        """检查目录是否可访问"""
        try:
            os.listdir(path)
            return True
        except PermissionError:
            self.log_time(f"[WARN] 无法访问目录（权限不足）: {path}")
        except FileNotFoundError:
            self.log_time(f"[WARN] 目录不存在: {path}")
        except OSError as e:
            self.log_time(f"[WARN] 无法进入目录 {path}: {e}")
        return False

    def get_file_hash(self, file_path):
        """计算文件 md5 哈希，用于校验内容"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def copyandcheckfiles(self, src_path, dst_path):
        try:
            print(f"[Copy] 复制文件：{src_path} -> {dst_path}")
            shutil.copy2(src_path, dst_path)  # 复制文件（包含元数据）
            #   log_time("开始 get_dir_info")
            src_hash = self.get_file_hash(src_path)
            dst_hash = self.get_file_hash(dst_path)
            #   log_time("结束 get_dir_info")
            if os.path.getsize(src_path) == os.path.getsize(dst_path) and src_hash == dst_hash:
                print(f"[Delete] 删除文件：{src_path}")
                os.remove(src_path)  # 目标文件src_path是文件时用os.remove 删除
            else:
                print(f"[!] 文件校验失败，不删除源: {src_path}")
        except Exception as e:
            print(f"[!] 复制文件出错: {src_path} -> {dst_path}, 错误: {e}")
        return

    def copyfiles(self, src_path, dst_path):
        # 忽略系统文件 thumbs.db
        if os.path.basename(src_path).lower() == "thumbs.db":
            print(f"[Skip] 跳过系统文件: {src_path}")
            return
        if os.path.exists(dst_path):  # 这里判断是否已经存在dst文件(重名)
            print(f"[Check] 存在重名文件：{src_path}")
            src_time = os.path.getmtime(src_path)
            dst_time = os.path.getmtime(dst_path)
            if src_time > dst_time:  # LM-Test内的文件时间更新 → 删除dst，保留src
                #   log_time("开始 copy 文件")
                print(f"[Check] LM-Test内的文件时间更新")
                self.copyandcheckfiles(src_path, dst_path)
                #   log_time("结束 copy 文件")
            else:  # SNxxxx内文件时间更新或一样新 → 直接删除src，保留dst
                print(f"[Check] 外部文件时间更新或一样新")
                print(f"[Delete] 删除文件{src_path}")
                os.remove(src_path)  # 是文件时用os.remove 删除
        else:  # 当目标不存在同名时，将LM-Test（src）里的文件或文件夹移动到SNxxxx（dst）
            #   log_time("开始 copy 文件")
            print(f"[Check] 不存在重名文件：{src_path}")
            self.copyandcheckfiles(src_path, dst_path)
            #   log_time("结束 copy 文件")
        return

    def copydir(self, src_path, dst_path):
        if not self.is_accessible(src_path):    # 这里判断是否能进入文件夹(权限问题等)
            self.log_time(f"[INFO] 跳过无法访问的目录: {src_path}")
            return

        if os.path.exists(dst_path):  # 这里判断是否已经存在dst文件夹(重名)
            print(f"[Check] 存在重名文件夹：{src_path}")
            # 目标存在时，逐个复制内容
            for item in os.listdir(src_path):
                src_item = os.path.join(src_path, item)
                dst_item = os.path.join(dst_path, item)
                self.movefolder(src_item, dst_item)
                # 循环结束后再检查 src_path 是否已空
            try:
                remaining = os.listdir(src_path)
                print(f"[Check] 剩余文件：{remaining}")
            except Exception as e:
                self.log_time(f"[ERROR] 无法列出 {src_path}: {e}")
                remaining = [ ]

            if not self.is_accessible(src_path):
                self.log_time(f"[INFO] 跳过删除不可访问目录: {src_path}")
            else:
                # 忽略的系统文件
                ignored = {"thumbs.db"}
                remaining_items = [f for f in remaining if f.lower() not in ignored]
                print(f"[Check] 当前文件夹：{src_path} 除Thumbs文件外为{remaining_items}")
                if not remaining_items:
                    try:
                        os.rmdir(src_path)
                        self.log_time(f"空文件夹删除: {src_path}")
                    except Exception as e:
                        self.log_time(f"[ERROR] 删除空目录失败 {src_path}: {e}")
                else:
                    # 打印出剩余的项及其 repr，方便排查
                    self.log_time(f"[INFO] {src_path} 仍有剩余 {len(remaining_items)} 项: {[repr(x) for x in remaining_items]}")
        else:
            try:
                print(f"[Copy] 复制文件：{src_path} -> {dst_path}")
                shutil.copytree(src_path, dst_path)  # 复制文件夹（包含元数据）
            except Exception as e:
                print(f"[!] 复制文件夹出错: {src_path} -> {dst_path}, 错误: {e}")
            # 检验复制完整性
            src_count, src_size, src_hashes = self.get_dir_info(src_path)
            dst_count, dst_size, dst_hashes = self.get_dir_info(dst_path)
            if src_count == dst_count and src_size == dst_size and src_hashes == dst_hashes:
                print(f"[Delete] 删除文件：{src_path}")
                shutil.rmtree(src_path)
                print(f"空文件夹删除: {src_path}")
                #   print(f"目录复制成功， 文件数 {dst_count}, 总大小 {dst_size} 字节")
            else:
                print(f"[!] 文件夹校验失败，不删除源: {src_path}")
        return

    def get_dir_info(self, path):
        # 递归统计文件夹内的文件数量和总大小
        total_size = 0
        file_count = 0
        file_hashes = dict()
        for root, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.isfile(fp):
                    file_count += 1
                    total_size += os.path.getsize(fp)
                    file_hashes[os.path.relpath(fp, path)] = self.get_file_hash(fp)
        return file_count, total_size, file_hashes

    def movefolder(self, src_path, dst_path):
        print(f"[Check] 当前检查文件{src_path}")
        if os.path.isfile(src_path):  # 这里判断源文件为文件而不是文件夹
            self.copyfiles(src_path, dst_path)
        elif os.path.isdir(src_path):  # 这里判断源文件为文件夹
            self.copydir(src_path, dst_path)
        return

    def detectfolder(self):
        #   先检测是否有LM-Test文件夹
        print(f'Current detecting Folder Name: {self.foldername}')
        print(f'Current detecting Folder Path: {self.path}')
        if not os.path.isdir(self.LMTest):
            print('No LM-Test inside')
            return

        # 先遍历除了01到09以外的的文件和文件夹
        # 允许的前缀：01, 02, ..., 09
        #   allowed_prefixes = [f"{i:02d}_" for i in range(1, 10)]

        for item in os.listdir(self.LMTest):
            src_path = os.path.join(self.LMTest, item)  # source 文件为LM-Test内部
            dst_path = os.path.join(self.path, item)  # destiny 文件为SNxxxx文件夹
            self.movefolder(src_path, dst_path)
        # 遍历完成后检查 LM-Test 内是否只剩 Thumbs.db 或空
        try:
            if not self.is_accessible(self.LMTest):
                self.log_time(f"[INFO] 跳过无法访问的 LM-Test: {self.LMTest}")
                return
            all_items = os.listdir(self.LMTest)
            print(f"[Check] 当前文件夹：{src_path} 剩余文件为{all_items}")
        except Exception as e:
            self.log_time(f"[ERROR] 无法列出 {self.LMTest}: {e}")
            all_items = []

        # 忽略的系统文件
        ignored = {"thumbs.db"}
        remaining_items = [f for f in all_items if f.lower() not in ignored]
        print(f"[Check] 当前文件夹：{src_path} 除Thumbs文件外为{remaining_items}")

        if not remaining_items:  # 如果空或只剩 Thumbs.db
            try:
                print(f"[Check] 当前文件夹：{src_path} 为空")
                shutil.rmtree(self.LMTest)
                print(f"已删除空的 LM-Test 文件夹: {self.LMTest}")
            except Exception as e:
                print(f"[!] 删除 LM-Test 失败: {e}")
        else:
            print(f"[Check] 当前文件夹：{src_path} 不为空")
            self.log_time(f"[INFO] LM-Test 仍有文件: {[repr(x) for x in remaining_items]}")
        return


class FolderWorker(QThread):
    progress_update = pyqtSignal(int, str)
    finished_signal = pyqtSignal(str)
    failed_files_signal = pyqtSignal(object)

    def __init__(self, folders, start_num, end_num):
        super().__init__()
        self.folders = folders
        self.start_num = start_num
        self.end_num = end_num

    def run(self):
        original_stdout = sys.stdout
        movement_name = f'Movement_{self.start_num}-{self.end_num}.txt'
        movement_path = os.path.join(r'D:/', movement_name)
        # 防止文件重名
        counter = 1
        while os.path.exists(movement_path):
            movement_path = os.path.join(r'D:/', f'Movement_{self.start_num}-{self.end_num}_{counter}.txt')
            counter += 1

        all_failed = {}
        with open(movement_path, 'w', encoding="utf-8") as file:
            sys.stdout = file
            for i, folder in enumerate(self.folders):
                folder_name = os.path.basename(folder)
                # 在此添加你的检测逻辑，例如检测特定文件
                detector = DetectFolders(folder)
                failed = detector.detectfolder()
                if failed:  # 合并到总失败列表
                    all_failed.update(failed)
                self.sleep(1)  # 模拟耗时操作
                self.progress_update.emit(i + 1, folder_name)
        sys.stdout = original_stdout
        self.failed_files_signal.emit(all_failed)  # 发送失败列表
        # 工作结束，发信号
        total = len(self.folders)
        self.finished_signal.emit(f"Detection succeeded.\n{total} folders checked.\nFile movement records saved.")


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

        self.tree_widget.clear()
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
        #   print(all_subfolders)

        self.progress_bar.setMaximum(len(all_subfolders))
        self.worker = FolderWorker(all_subfolders, start_num, end_num)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.finished_signal.connect(self.show_message)  # 接收线程FolderWorker中发送的弹窗信号
        self.worker.start()
        self.worker.failed_files_signal.connect(self.display_failed_files)

    def update_progress(self, value, folder_name):
        self.progress_bar.setValue(value)
        self.status_label.setText(f'Now detecting: {folder_name}')

    def show_message(self, msg):
        QMessageBox.information(self, 'Movement Saved', msg)
        self.status_label.setText('Finished.')

    def display_failed_files(self, all_failed_dict):
        for folder_name, file_list in all_failed_dict.items():
            self.add_remaining_files_to_tree(folder_name, file_list)

    def add_remaining_files_to_tree(self, folder_name, file_list):
        folder_item = QTreeWidgetItem([folder_name])
        self.tree_widget.addTopLevelItem(folder_item)

        for file_path in file_list:
            file_item = QTreeWidgetItem([os.path.basename(file_path), '', ''])
            folder_item.addChild(file_item)

            open_button = QPushButton("Open")
            open_button_widget = QWidget()
            layout = QHBoxLayout(open_button_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(open_button)
            open_button.clicked.connect(lambda checked, path=file_path: self.open_file_location(path))

            self.tree_widget.setItemWidget(file_item, 1, open_button_widget)

    def open_file_location(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, "File Not Found", f"The file does not exist:\n{path}")
            return

        if platform.system() == "Windows":
            # 选中文件而不是仅仅打开文件夹
            subprocess.run(['explorer', '/select,', os.path.normpath(path)])
        elif platform.system() == "Darwin":
            subprocess.run(['open', '-R', path])
        else:
            subprocess.run(['xdg-open', os.path.dirname(path)])


if __name__ == '__main__':
    try:
        app = QApplication([])
        window = MainWindow()
        window.show()
        app.exec()
    except Exception as e:
        print(f"[ERROR] 程序崩溃: {e}")
    finally:
        input("按回车键退出程序...")
    # app = QApplication([])
    # window = MainWindow()
    # window.show()
    # app.exec()
