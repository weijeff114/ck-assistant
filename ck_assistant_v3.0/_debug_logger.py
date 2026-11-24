# -*- coding: utf-8 -*-
"""全局异常与日志捕捉模块（非侵入式）。
在 main.py 顶部调用 install_global_logging() 即可把所有异常、
Qt 事件循环错误、以及关键函数调用细节写入 debug_log.txt。
"""
import sys, os, logging, traceback, datetime

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug_log.txt')


def _make_logger():
    logger = logging.getLogger('cf_debug')
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        fh = logging.FileHandler(LOG_FILE, 'a', encoding='utf-8')
        fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        # 同时镜像到控制台，方便在线观察
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        logger.addHandler(ch)
    return logger

logger = _make_logger()

_original_excepthook = sys.excepthook


def _global_excepthook(exc_type, exc_value, exc_tb):
    """捕获所有未处理异常并连同完整调用栈写入日志。"""
    try:
        lines = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.critical('=== UNCAUGHT EXCEPTION ===\n%s', lines)
    except Exception:
        pass
    # 仍交给原 hook，保证程序原行为不变
    _original_excepthook(exc_type, exc_value, exc_tb)


def install_global_logging():
    """安装全局异常钩子，并在日志中记录启动时刻。"""
    sys.excepthook = _global_excepthook

    # 捕获 Qt 消息（警告/致命），Qt 事件循环中的异常常重定向到 stderr
    try:
        from PyQt5 import QtCore
        def qt_message_handler(mode, context, message):
            try:
                logger.warning('[Qt %s] %s | 位置: %s:%d (%s)', mode, message, context.file, context.line, context.function)
            except Exception:
                pass
        QtCore.qInstallMessageHandler(qt_message_handler)
    except Exception:
        pass

    logger.info('========== CF Debug Logging 启动 %s ==========',
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
def log(message, level='info'):
    """供业务代码调用的轻量日志入口，写入 debug_log.txt。"""
    try:
        getattr(logger, level)(message)
    except Exception:
        try:
            logger.info(message)
        except Exception:
            pass
