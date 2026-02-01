# hook-boot_win7_fix.py
"""
启动阶段修复钩子
"""
hiddenimports = []

# 预导入替代模块
import sys
import os

# 设置兼容环境
os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '1'
os.environ['PYINSTALLER_WIN7_COMPAT'] = '1'

# 创建空的expat模块避免导入错误
class DummyExpat:
    def ParserCreate(self, *args, **kwargs):
        class DummyParser:
            def Parse(self, *args, **kwargs): return True
            def ParseFile(self, *args, **kwargs): return True
        return DummyParser()

sys.modules['pyexpat'] = DummyExpat()
sys.modules['xml.parsers.expat'] = DummyExpat()

print("启动钩子：pyexpat 替代模块已加载")
