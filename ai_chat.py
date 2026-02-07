import sys
import os
import threading
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTextEdit, QLineEdit,
                             QPushButton, QLabel, QHBoxLayout)
from PyQt5.QtCore import pyqtSignal, QObject, Qt

# 尝试导入，防止未安装报错
try:
    from llama_cpp import Llama

    HAS_LLAMA = True
except ImportError:
    HAS_LLAMA = False


def get_base_path():
    """获取程序运行的基础路径（兼容IDE运行和打包后的exe）"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 exe，资源文件通常在 exe 同级目录下
        return os.path.dirname(sys.executable)
    else:
        # 如果是 PyCharm 开发环境，使用当前文件所在目录
        return os.path.dirname(os.path.abspath(__file__))


class AIWorker(QObject):
    """在后台线程运行AI推理，防止界面卡死"""
    finished = pyqtSignal(str)

    def __init__(self, model_path, system_prompt, user_query):
        super().__init__()
        self.model_path = model_path
        self.system_prompt = system_prompt
        self.user_query = user_query

    def run(self):
        if not HAS_LLAMA:
            self.finished.emit("错误: 未检测到 llama-cpp-python 库。\n请确保已安装该库，且环境配置正确。")
            return

        if not os.path.exists(self.model_path):
            self.finished.emit(
                f"错误: 找不到模型文件。\n预期路径: {self.model_path}\n请确保在exe同级目录下创建了 'models' 文件夹并放入了模型。")
            return

        try:
            # 加载模型
            # n_ctx: 上下文长度。2048 对于 4GB-8GB 内存的老电脑比较安全。
            # n_threads: CPU线程数，设为4以平衡性能和系统响应。
            # n_gpu_layers: 设为0，强制使用CPU，避免 Win7 显卡驱动兼容性问题。
            llm = Llama(
                model_path=self.model_path,
                n_ctx=2048,
                n_threads=4,
                n_gpu_layers=0,
                verbose=False
            )

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self.user_query}
            ]

            # 开始推理
            output = llm.create_chat_completion(messages=messages, temperature=0.7)
            response = output['choices'][0]['message']['content']
            self.finished.emit(response)
        except Exception as e:
            self.finished.emit(f"AI 运行出错: {str(e)}\n(可能是内存不足或模型文件损坏)")


class AIChatDialog(QDialog):
    def __init__(self, data_context, parent=None):
        super().__init__(parent)
        self.data_context = data_context  # 这是从查询结果传来的数据字符串

        # --- 动态构建模型路径 ---
        base_path = get_base_path()
        # 注意：这里定义了模型文件名，必须与你下载的文件名完全一致！
        model_filename = "qwen1_5-1_8b-chat-q4_k_m.gguf"
        # 拼接路径：程序根目录/models/模型文件名
        self.model_path = os.path.join(base_path, "models", model_filename)
        # --------------------------------

        self.setWindowTitle("智能数据助手 (离线版)")
        self.resize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        layout.addWidget(self.chat_history)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("请输入您的问题，例如：'帮我总结一下这些人的学历情况'...")
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self.start_inference)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)

        # === 修复点：使用 addLayout 而不是 addWidget ===
        layout.addLayout(input_layout)
        # ============================================

        # 状态检查与显示
        status_text = "就绪 (本地CPU模式)"
        if not HAS_LLAMA:
            status_text = "错误：缺少运行库 llama-cpp-python"
            self.send_btn.setEnabled(False)
        elif not os.path.exists(self.model_path):
            status_text = f"错误：未找到模型文件 (请检查 models 文件夹)"

        self.status_label = QLabel(status_text)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def start_inference(self):
        question = self.input_field.text().strip()
        if not question:
            return

        self.chat_history.append(f"<b>我:</b> {question}")
        self.input_field.clear()
        self.send_btn.setEnabled(False)
        self.status_label.setText("AI 正在思考中... (这可能需要一些时间)")

        # 构建提示词 (Prompt Engineering)
        system_prompt = (
            "你是一个专业的人事管理助手。请基于以下提供的员工数据回答用户问题。\n"
            "数据中包含员工的姓名、职务、学历等信息。\n"
            "-------------------\n"
            f"{self.data_context}\n"
            "-------------------\n"
            "要求：\n"
            "1. 仅根据上述数据回答，不要编造。\n"
            "2. 如果数据中没有答案，请直接说明“数据中未包含相关信息”。\n"
            "3. 回答要简洁明了。"
        )

        # 启动后台线程
        self.worker = AIWorker(self.model_path, system_prompt, question)
        self.worker_thread = threading.Thread(target=self.worker.run)
        self.worker.finished.connect(self.handle_response)
        self.worker_thread.start()

    def handle_response(self, response):
        self.chat_history.append(f"<b>AI:</b> {response}")

        # 自动滚动到底部
        scrollbar = self.chat_history.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        self.send_btn.setEnabled(True)
        self.status_label.setText("就绪")
