import os
import shutil
import subprocess


def clean_old_builds():
    """清理之前的打包文件和目录"""
    print("开始清理旧的打包文件...")
    # 把新旧两种名称的 .spec 文件都加入清理列表
    items_to_remove = ['build', 'dist', '人员信息管理系统.spec', 'PersonnelSystem.spec']
    for item in items_to_remove:
        if os.path.exists(item):
            try:
                if os.path.isdir(item):
                    shutil.rmtree(item)
                else:
                    os.remove(item)
                print(f"已清理: {item}")
            except Exception as e:
                print(f"清理 {item} 失败: {e}")


def build_app():
    """使用 PyInstaller 打包应用为单文件"""
    print("\n开始打包程序 (单文件模式)...")

    # 确保当前目录下有 bin 文件夹存在，否则无法打包进去
    if not os.path.exists("bin"):
        print("警告: 当前目录下没有找到 bin 文件夹！请确保 bin 文件夹存在后再打包。")

    command = [
        "pyinstaller",
        "-F",  # 打包成单个 exe 文件
        "-w",  # 隐藏控制台窗口
        "-i", "app_icon.ico",  # 设置 exe 文件的外部图标
        "-n", "人员信息管理系统",
        "--noconfirm",
        # 【新增这行】把图标文件作为数据打包进 exe 的根目录，供程序运行时读取
        "--add-data", "app_icon.ico;.",
        "main.py"
    ]

    try:
        subprocess.run(command, check=True)
        print("\n打包完成！")
        print("打包后的单文件位于 'dist/人员信息管理系统.exe'。")
        print("现在你只需要把外部的 'models'和'bin' 文件夹和 '人员信息管理系统.exe' 放在同一个目录下即可运行。")
    except subprocess.CalledProcessError as e:
        print(f"\n打包发生错误: {e}")


if __name__ == "__main__":
    clean_old_builds()
    build_app()