# pyi_rth_disable_multiprocessing.py
import sys
import os

class FakeMultiprocessingModule:
    def __getattr__(self, name):
        def dummy_function(*args, **kwargs):
            raise NotImplementedError("多进程功能已禁用以提高 Windows 7 兼容性")
        return dummy_function

# 替换问题模块
fake_mp = FakeMultiprocessingModule()
problematic_modules = [
    'multiprocessing', 'multiprocessing.context', 'multiprocessing.spawn',
    'multiprocessing.forkserver', 'multiprocessing.reduction', '_multiprocessing',
    'concurrent.futures', 'concurrent.futures.process'
]

for module_name in problematic_modules:
    sys.modules[module_name] = fake_mp

# 禁用多进程环境变量
os.environ.update({
    'DISABLE_MULTIPROCESSING': '1',
    'MULTIPROCESSING_FORCE': '0',
    'PYTHONDONTWRITEBYTECODE': '1'
})

print("✓ Windows 7 兼容性钩子已加载")
