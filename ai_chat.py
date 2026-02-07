import sys
import os
import threading
import traceback
import markdown  # 【新增】导入 markdown 库用于文本渲染
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
            print(f"DEBUG: 正在尝试加载模型: {self.model_path}")

            # 加载模型
            # n_ctx: 上下文长度。2048 对于 4GB-8GB 内存的老电脑比较安全。
            # n_threads: CPU线程数，设为4以平衡性能和系统响应。
            # n_gpu_layers: 设为0，强制使用CPU，避免 Win7 显卡驱动兼容性问题。
            llm = Llama(
                model_path=self.model_path,
                n_ctx=2048,
                n_threads=4,
                n_gpu_layers=0,
                verbose=True
            )

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self.user_query}
            ]

            print("DEBUG: 模型加载成功，开始推理...")

            # 开始推理
            output = llm.create_chat_completion(messages=messages, temperature=0.7)
            response = output['choices'][0]['message']['content']
            self.finished.emit(response)

        except Exception as e:
            print("\n" + "=" * 50)
            print("!!! AIWorker 发生严重错误 !!!")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误详情: {str(e)}")
            print("-" * 30)
            print("完整堆栈信息 (Traceback):")
            traceback.print_exc()
            print("=" * 50 + "\n")

            # 将错误信息发送回界面显示
            self.finished.emit(f"AI 运行出错: {str(e)}\n(可能是内存不足或模型文件损坏)")


class AIChatDialog(QDialog):
    def __init__(self, data_context, parent=None):
        super().__init__(parent)
        self.data_context = data_context  # 这是从查询结果传来的数据字符串

        # --- 【修改开始】自动识别模型路径 ---
        base_path = get_base_path()
        models_dir = os.path.join(base_path, "models")

        # 初始化默认值
        self.model_path = ""

        # 1. 检查 models 文件夹是否存在
        if os.path.exists(models_dir):
            # 2. 获取所有 .gguf 文件
            # 列表推导式：遍历目录，找到所有以 .gguf 结尾的文件
            gguf_files = [f for f in os.listdir(models_dir) if f.endswith('.gguf')]

            if gguf_files:
                # 3. 自动选择第一个模型 (按名称排序，保证顺序稳定)
                gguf_files.sort()
                selected_model = gguf_files[0]
                self.model_path = os.path.join(models_dir, selected_model)
                print(f"系统自动选中模型: {selected_model}")
            else:
                # 文件夹存在但没有模型文件
                self.model_path = os.path.join(models_dir, "未找到.gguf模型文件")
        else:
            # models 文件夹根本不存在
            self.model_path = os.path.join(base_path, "models_文件夹缺失")

        self.setWindowTitle("智能助手 (离线版)")
        self.resize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        layout.addWidget(self.chat_history)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("请输入您的问题：")
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self.start_inference)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)

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
        self.status_label.setText("AI 正在思考中... ")

        # 构建提示词 (Prompt Engineering)
        # 【修改点2】增加 Markdown 格式要求
        system_prompt = (
            "你是一个专业的人事管理助手。请基于以下提供的员工数据回答用户问题。\n"
            "数据中包含员工的姓名、职务、学历等信息。\n"
            "-------------------\n"
            f"{self.data_context}\n"
            "-------------------\n"
            "要求：\n"
            "1. 仅根据上述数据回答，不要编造。\n"
            "2. 如果数据中没有答案，请直接说明“数据中未包含相关信息”。\n"
            "3. 回答要简洁明了。\n"
            "4. 【重要】请使用 Markdown 格式优化排版：\n"
            "   - 使用无序列表（- 项目）列举多人信息。\n"
            "   - 使用粗体（**内容**）强调人名或关键数据。\n"
            "   - 适当分段，不要输出一大块文本。"
        )

        # 启动后台线程
        self.worker = AIWorker(self.model_path, system_prompt, question)
        self.worker_thread = threading.Thread(target=self.worker.run)
        self.worker.finished.connect(self.handle_response)
        self.worker_thread.start()

    def handle_response(self, response):
        # 【修改点3】将 Markdown 转换为 HTML 并美化显示

        # 1. 转换 Markdown 为 HTML
        try:
            # extensions=['extra'] 支持更多语法（如表格、定义列表等）
            html_content = markdown.markdown(response, extensions=['extra'])
        except Exception as e:
            print(f"Markdown 转换失败: {e}")
            # 降级处理：如果转换失败，直接显示原始文本（将换行符转为HTML换行）
            html_content = response.replace('\n', '<br>')

        # 2. 定义 CSS 样式（美化列表、段落间距和粗体颜色）
        styled_html = f"""
        <style>
            p {{ margin-bottom: 8px; line-height: 1.6; }}
            ul {{ margin-bottom: 8px; margin-left: 15px; }}
            li {{ margin-bottom: 4px; }}
            strong {{ color: #003366; font-weight: bold; }}
            h1, h2, h3 {{ color: #003366; margin-top: 10px; margin-bottom: 5px; }}
        </style>
        <div>{html_content}</div>
        """

        # 3. 添加到聊天窗口
        self.chat_history.append(f"<b>AI:</b><br>{styled_html}")
        self.chat_history.append("<hr>")  # 添加分割线

        # 自动滚动到底部
        scrollbar = self.chat_history.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        self.send_btn.setEnabled(True)
        self.status_label.setText("就绪")
