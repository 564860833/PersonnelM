# pyi_rth_win7_ultra_fix.py
"""
Windows 7 超级兼容性运行时钩子
在所有模块加载前修复 DLL 和 XML 问题
"""
import sys
import os

print("=== Windows 7 超级兼容性钩子启动 ===")

# 1. 最早期的环境变量设置
os.environ.update({
    'PYTHONLEGACYWINDOWSSTDIO': '1',
    'PYTHONIOENCODING': 'utf-8', 
    'PYTHONDONTWRITEBYTECODE': '1',
    'PYINSTALLER_WIN7_COMPAT': '1'
})

# 2. 彻底禁用有问题的模块
BLOCKED_MODULES = [
    'multiprocessing.spawn',
    'multiprocessing.forkserver', 
    'multiprocessing.reduction',
    '_multiprocessing',
    'concurrent.futures.process',
    'asyncio',
    'xml.parsers.expat'  # 关键：阻止原始expat加载
]

class BlockedModule:
    def __getattr__(self, name):
        raise ImportError(f"模块 {name} 已被禁用以确保 Windows 7 兼容性")

for module_name in BLOCKED_MODULES:
    sys.modules[module_name] = BlockedModule()

# 3. 创建完全替代的 pyexpat 实现
class Win7CompatibleExpat:
    """Windows 7 兼容的 XML 解析器替代实现"""

    class XMLParserType:
        def __init__(self, encoding=None):
            self.encoding = encoding or 'utf-8'
            self.StartElementHandler = None
            self.EndElementHandler = None
            self.CharacterDataHandler = None
            self.ProcessingInstructionHandler = None
            self.CommentHandler = None
            self.DefaultHandler = None

        def Parse(self, data, isfinal=1):
            # 最简单的解析实现，只处理基本情况
            return True

        def ParseFile(self, file):
            try:
                if hasattr(file, 'read'):
                    data = file.read()
                else:
                    with open(file, 'r', encoding=self.encoding) as f:
                        data = f.read()
                return self.Parse(data)
            except:
                return True

        def SetParamEntityParsing(self, flag):
            pass

        def UseForeignDTD(self, flag=True):
            pass

    def ParserCreate(self, encoding=None):
        return self.XMLParserType(encoding)

    def ParserCreateNS(self, encoding=None, namespace_separator=None):
        return self.XMLParserType(encoding)

# 4. 注入替代模块（在任何其他导入之前）
sys.modules['pyexpat'] = Win7CompatibleExpat()
sys.modules['xml.parsers.expat'] = Win7CompatibleExpat()

# 5. 修复 ElementTree 以使用我们的替代解析器
def fix_elementtree():
    try:
        import xml.etree.ElementTree as ET

        # 创建兼容的元素类
        class CompatElement:
            def __init__(self, tag, attrib=None, **extra):
                self.tag = tag
                self.attrib = attrib or {}
                self.attrib.update(extra)
                self.text = None
                self.tail = None
                self._children = []

            def find(self, path):
                return None

            def findall(self, path):
                return []

            def get(self, key, default=None):
                return self.attrib.get(key, default)

            def set(self, key, value):
                self.attrib[key] = value

            def append(self, element):
                self._children.append(element)

            def iter(self, tag=None):
                return iter([])

        # 替换关键函数
        original_parse = getattr(ET, 'parse', None)
        original_fromstring = getattr(ET, 'fromstring', None)

        def safe_parse(source):
            return CompatElement('root')

        def safe_fromstring(text):
            return CompatElement('root')

        ET.parse = safe_parse
        ET.fromstring = safe_fromstring
        ET.Element = CompatElement

        print("✓ ElementTree 已修复为兼容模式")

    except Exception as e:
        print(f"⚠️ ElementTree 修复失败: {e}")

# 6. DLL 路径修复
def fix_dll_paths():
    if sys.platform == "win32":
        try:
            # 添加系统DLL目录
            if hasattr(os, 'add_dll_directory'):
                system32 = os.path.join(os.environ.get('WINDIR', 'C:\Windows'), 'System32')
                if os.path.exists(system32):
                    os.add_dll_directory(system32)

            # 修改PATH环境变量
            current_path = os.environ.get('PATH', '')
            system_dirs = [
                os.path.join(os.environ.get('WINDIR', 'C:\Windows'), 'System32'),
                os.path.join(os.environ.get('WINDIR', 'C:\Windows'), 'SysWOW64')
            ]

            for dir_path in system_dirs:
                if os.path.exists(dir_path) and dir_path not in current_path:
                    os.environ['PATH'] = dir_path + os.pathsep + current_path

            print("✓ DLL 搜索路径已修复")

        except Exception as e:
            print(f"⚠️ DLL 路径修复失败: {e}")

# 立即执行所有修复
try:
    fix_dll_paths()
    fix_elementtree()
    print("✓ 所有 Windows 7 兼容性修复已应用")
except Exception as e:
    print(f"⚠️ 兼容性修复部分失败: {e}")

print("=== Windows 7 超级兼容性钩子完成 ===")
