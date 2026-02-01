import sys
import os

# 在所有导入之前设置环境
os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '1'
os.environ['PYINSTALLER_WIN7_COMPAT'] = '1'

# 创建空的pyexpat模块
class DummyExpat:
    def ParserCreate(self, *args): 
        class P:
            def Parse(self, *args): return True
            def ParseFile(self, *args): return True
        return P()

sys.modules['pyexpat'] = DummyExpat()
sys.modules['xml.parsers.expat'] = DummyExpat()
