# pyi_rth_win7_compat.py
import sys
import os

# Windows 7 兼容性修复
if sys.platform == "win32":
    try:
        win_version = sys.getwindowsversion()
        if win_version.major == 6 and win_version.minor == 1:  # Windows 7
            # 禁用多进程以提高兼容性
            os.environ["DISABLE_MULTIPROCESSING"] = "1"

            # 修复环境变量
            os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
            os.environ["QT_SCALE_FACTOR"] = "1"

            # 修复 DLL 加载问题
            if hasattr(os, 'add_dll_directory'):
                # Python 3.8+ 需要显式添加系统目录
                system_path = os.environ.get('SystemRoot', '') + '\System32'
                if os.path.exists(system_path):
                    os.add_dll_directory(system_path)

            # 修复日志编码问题
            try:
                sys.stdout.reconfigure(encoding='utf-8')
                sys.stderr.reconfigure(encoding='utf-8')
            except AttributeError:
                pass

            print("✓ Windows 7 兼容性修复已应用")
    except Exception as e:
        print(f"应用Windows 7兼容性修复失败: {e}")
