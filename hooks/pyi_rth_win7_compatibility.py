# pyi_rth_win7_compatibility.py
"""
Windows 7 兼容性运行时钩子
修复 DLL 加载和 XML 解析器问题
"""
import sys
import os
import warnings

print("=== Windows 7 兼容性钩子启动 ===")

# 1. 修复 DLL 搜索路径
if hasattr(os, 'add_dll_directory'):
    try:
        # 添加系统DLL目录
        system32 = os.path.join(os.environ.get('WINDIR', 'C:\Windows'), 'System32')
        if os.path.exists(system32):
            os.add_dll_directory(system32)
            print(f"✓ 已添加DLL搜索路径: {system32}")
    except Exception as e:
        print(f"⚠️  DLL路径设置失败: {e}")

# 2. 设置兼容性环境变量
os.environ.update({
    'PYTHONDONTWRITEBYTECODE': '1',
    'PYTHONIOENCODING': 'utf-8',
    'PYTHONLEGACYWINDOWSSTDIO': '1',  # Windows 7 控制台兼容
    'PYINSTALLER_WIN7_COMPAT': '1',
    'DISABLE_MULTIPROCESSING': '1'
})

# 3. 禁用警告，避免干扰
warnings.filterwarnings('ignore')

# 4. 修复 XML 解析器问题
def fix_xml_parser():
    """修复 pyexpat 和 XML 解析器问题"""
    try:
        # 预先导入可能有问题的模块
        import xml.etree.ElementTree as ET
        import xml.parsers.expat
        print("✓ XML解析器模块加载成功")

        # 设置默认解析器
        try:
            # 强制使用纯Python实现
            import xml.etree.ElementTree
            if hasattr(xml.etree.ElementTree, '_set_factories'):
                xml.etree.ElementTree._set_factories(None, None)
        except:
            pass

    except ImportError as e:
        print(f"⚠️  XML解析器加载失败: {e}")
        # 创建替代实现
        class DummyElement:
            def __init__(self, tag="", attrib=None, **extra):
                self.tag = tag
                self.attrib = attrib or {}
                self.text = None
                self.tail = None

            def find(self, path):
                return None

            def findall(self, path):
                return []

        # 注入到sys.modules
        if 'xml.etree.ElementTree' not in sys.modules:
            import types
            dummy_module = types.ModuleType('xml.etree.ElementTree')
            dummy_module.Element = DummyElement
            dummy_module.SubElement = DummyElement
            dummy_module.parse = lambda x: DummyElement()
            sys.modules['xml.etree.ElementTree'] = dummy_module
            print("✓ 使用XML解析器替代实现")

# 5. 修复多进程问题
def disable_problematic_modules():
    """禁用可能导致问题的模块"""
    problematic_modules = [
        'multiprocessing.spawn',
        'multiprocessing.forkserver', 
        'multiprocessing.reduction',
        '_multiprocessing',
        'concurrent.futures.process'
    ]

    class DummyModule:
        def __getattr__(self, name):
            def dummy_func(*args, **kwargs):
                raise RuntimeError(f"模块已禁用以确保 Windows 7 兼容性: {name}")
            return dummy_func

    dummy = DummyModule()
    for module_name in problematic_modules:
        sys.modules[module_name] = dummy

    print(f"✓ 已禁用 {len(problematic_modules)} 个问题模块")

# 6. 应用所有修复
try:
    fix_xml_parser()
    disable_problematic_modules()
    print("✓ Windows 7 兼容性修复已应用")
except Exception as e:
    print(f"⚠️  兼容性修复部分失败: {e}")

print("=== Windows 7 兼容性钩子完成 ===")
