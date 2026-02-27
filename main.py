import sys
import os
import logging
import PyQt5

#获得 PyQt5 的安装路径
pyqt5_dirname = os.path.dirname(PyQt5.__file__)

# 尝试构建插件路径 (根据 PyQt5 版本不同，路径可能在 Qt/plugins 或 Qt5/plugins)
plugin_path = os.path.join(pyqt5_dirname, 'Qt5', 'plugins')
if not os.path.exists(plugin_path):
    plugin_path = os.path.join(pyqt5_dirname, 'Qt', 'plugins')

# 设置环境变量，告诉 Qt 插件在哪里
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

print(f"Qt 插件路径已设置为: {plugin_path}")


# 现在安全导入其他模块
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox
from config import config
from database import Database
from login import LoginDialog
from main_window import MainWindow

# 全局主窗口引用，防止被垃圾回收
global_main_window = None

# 设置主日志记录器
logger = logging.getLogger('Main')


def resource_path(relative_path):
    """获取资源绝对路径，适用于开发环境和PyInstaller打包环境"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller创建的临时文件夹
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def create_safe_application():
    """创建兼容 Windows 7 的 Qt 应用程序"""
    try:
        app = QApplication(sys.argv)
        app.setApplicationName(config.APP_NAME)
        app.setApplicationVersion(config.APP_VERSION)

        # ============= 设置应用程序图标 (新增部分) =============
        try:
            # 使用资源路径函数获取图标路径
            icon_path = resource_path('app_icon.ico')
            logger.info(f"尝试加载应用程序图标: {icon_path}")

            # 注册应用 AppUserModelID (适用于 Win10/Win11，确保任务栏图标独立且正确显示)
            if sys.platform == "win32":
                import ctypes
                try:
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('PersonnelSystem')
                except Exception as e:
                    logger.error(f"注册应用ID失败: {e}")

            # 创建并设置图标
            if os.path.exists(icon_path):
                app_icon = QIcon(icon_path)
                app.setWindowIcon(app_icon)
                logger.info("应用程序图标已设置")
            else:
                logger.warning(f"图标文件不存在: {icon_path}")
        except Exception as e:
            logger.error(f"设置应用程序图标失败: {e}")
            app_icon = QIcon()
            app.setWindowIcon(app_icon)
        # ===================================================

        return app
    except Exception as e:
        logger.error(f"创建应用程序失败: {e}")
        # 尝试最小化创建
        try:
            app = QApplication([])
            # 尝试设置空图标
            try:
                app_icon = QIcon()
                app.setWindowIcon(app_icon)
            except:
                pass
            return app
        except:
            raise Exception("无法创建 Qt 应用程序")


def main():
    """应用程序主入口"""
    try:
        # 创建Qt应用程序
        app = create_safe_application()

        # 设置应用程序图标（任务栏图标） - 使用资源路径函数
        try:
            app_icon = QIcon(resource_path('app_icon.ico'))
            app.setWindowIcon(app_icon)
        except:
            # 忽略图标加载失败
            app_icon = QIcon()
            pass

        # 设置全局字体
        try:
            app.setFont(config.font())
        except:
            # 使用默认字体
            pass

        # 直接进入初始化流程
        logger.info("应用程序启动")

        # 初始化数据库
        logger.info("正在初始化数据库...")
        db = Database()

        # 确保管理员账号存在
        if db.get_password('admin') is None:
            db.change_password('admin', '123456')
            logger.info("管理员账号已创建: admin/123456")

        # 检查数据库连接状态
        if not check_database_connection(db):
            logger.error("数据库连接失败，应用程序将退出")
            QMessageBox.critical(None, "数据库错误", "无法连接到数据库，应用程序将退出")
            return app.exec_()

        logger.info("数据库初始化成功")

        # 创建并显示登录对话框 - 使用资源路径函数设置图标
        login_dialog = LoginDialog(db)
        try:
            login_dialog.setWindowIcon(app_icon)
        except:
            pass

        # 显示登录窗口
        if login_dialog.exec_() == LoginDialog.Accepted:
            # 登录成功，创建主窗口
            username = login_dialog.get_username()
            logger.info(f"用户 {username} 登录成功")

            # 获取用户权限
            permissions = db.get_user_permissions(username)

            # 管理员自动拥有所有权限
            if username.lower() == 'admin':
                permissions = {
                    'base_info': True,
                    'rewards': True,
                    'family': True,
                    'resume': True
                }
                logger.info(f"管理员账号 {username} 获得所有权限")

            try:
                global global_main_window
                global_main_window = MainWindow(db, username, permissions)  # 传递3个参数
                # 为主窗口设置图标
                try:
                    global_main_window.setWindowIcon(app_icon)
                except:
                    pass

                global_main_window.showMaximized()

                # 进入主事件循环
                return app.exec_()

            except Exception as e:
                logger.exception("创建主窗口失败")
                QMessageBox.critical(None, "启动失败", f"无法启动主窗口: {str(e)}")
                return app.exec_()
        else:
            # 用户取消登录或登录失败
            logger.info("用户取消登录，应用程序将退出")
            db.close()
            return app.exec_()

    except Exception as e:
        logger.exception("应用程序初始化过程中发生错误")
        try:
            show_critical_error("系统初始化错误", f"无法启动应用程序: {str(e)}")
        except:
            print(f"致命错误: {str(e)}")
        return 1


def check_database_connection(db) -> bool:
    """检查数据库连接状态"""
    try:
        # 执行简单的查询测试
        cursor = db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        # 确保所有必需的表格存在
        required_tables = ['base_info', 'rewards', 'family', 'resume', 'users', 'user_permissions']
        existing_tables = [table[0] for table in tables]
        missing_tables = [t for t in required_tables if t not in existing_tables]

        if missing_tables:
            logger.warning(f"数据库缺失以下表格: {', '.join(missing_tables)}")
            # 尝试创建缺失的表
            db.create_tables()

            # 再次检查是否创建成功
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables_after = [table[0] for table in cursor.fetchall()]
            if any(t not in tables_after for t in missing_tables):
                logger.error(f"无法创建缺失的表格: {', '.join(missing_tables)}")
                return False

        return True
    except Exception as e:
        logger.error(f"数据库连接检查失败: {str(e)}")
        return False


def show_critical_error(title, message):
    """显示严重错误消息框"""
    try:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText("严重错误")
        msg_box.setInformativeText(message)
        msg_box.setStandardButtons(QMessageBox.Close)
        msg_box.exec_()
    except:
        print(f"错误: {title} - {message}")


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"程序异常退出: {e}")
        sys.exit(1)
