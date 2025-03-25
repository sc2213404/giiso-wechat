
import inspect
import os
from pathlib import Path
import sys
import logging, logging.config
from logging.handlers import TimedRotatingFileHandler
import shutil
import yaml


# log_path = r'./logs/'
# # 如果目录不存在，则创建目录
# target_dir = Path(log_path)
# target_dir.mkdir(parents=True, exist_ok=True)
# level = logging.DEBUG


class CustomLogger:
    def __init__(self, name, log_file=None):
        yconfig = self._load_config()

        # 日志文件路径替换占位符
        chat_channel = yconfig['giiso']['chat_channel']
        for handler in yconfig['logging']['handlers'].values():
            if isinstance(handler, dict) and 'filename' in handler:
                handler['filename'] = handler['filename'].replace("{chat_channel}", chat_channel)

                # 获取目录部分
                log_dir = os.path.dirname(handler['filename'])

                # 检查目录是否存在，如果不存在则创建
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)

        logging.config.dictConfig(yconfig["logging"])
        self.logger = logging.getLogger(name)
        # self.logger.setLevel(level)

        # formatter = logging.Formatter(
        #     "[%(asctime)s] [%(process)d:%(processName)s] [%(thread)d:%(threadName)s] [%(levelname)s] %(message)s")
        #
        # if log_file:
        #     log_file_handler = TimedRotatingFileHandler(filename=log_file, when="D", interval=1, encoding='utf-8')
        #     log_file_handler.setFormatter(formatter)
        #     log_file_handler.setLevel(level)
        #     self.logger.addHandler(log_file_handler)

        # stream_handler = logging.StreamHandler(sys.stdout)
        # stream_handler.setFormatter(formatter)
        # stream_handler.setLevel(level)
        # self.logger.addHandler(stream_handler)

    def get_logger(self):
        return self.logger

    def _load_config(self) -> dict:
        pwd = os.path.dirname(os.path.abspath(__file__))
        try:
            with open(f"{pwd}/config.yaml", "rb") as fp:
                yconfig = yaml.safe_load(fp)
        except FileNotFoundError:
            shutil.copyfile(f"{pwd}/config.yaml.template", f"{pwd}/config.yaml")
            with open(f"{pwd}/config.yaml", "rb") as fp:
                yconfig = yaml.safe_load(fp)

        return yconfig

# 创建一个自定义的Logger类，它在记录错误时自动包含堆栈跟踪信息
class ExceptionLoggingLoggerAdapter:
    def __init__(self, logger):
        self.logger = logger

    def _get_caller_info(self):
        # 使用 inspect 来获取调用者的信息
        frame = inspect.stack()[2]  # 获取调用栈的第二个帧（即调用日志函数的帧）
        filename = frame.filename.split("\\")[-1]  # 获取文件名（只保留文件名，去掉路径）
        lineno = frame.lineno  # 获取调用行号
        return filename, lineno

    def error(self, msg, *args, **kwargs):
        kwargs['exc_info'] = kwargs.get('exc_info', True)
        filename, lineno = self._get_caller_info()  # 获取调用信息
        self.logger.error(f"[{filename}:{lineno}] - {msg}", *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        filename, lineno = self._get_caller_info()  # 获取调用信息
        self.logger.debug(f"[{filename}:{lineno}] - {msg}", *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        filename, lineno = self._get_caller_info()  # 获取调用信息
        self.logger.info(f"[{filename}:{lineno}] - {msg}", *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        filename, lineno = self._get_caller_info()  # 获取调用信息
        self.logger.warning(f"[{filename}:{lineno}] - {msg}", *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)


custom_logger = CustomLogger('Robot')
logger = ExceptionLoggingLoggerAdapter(custom_logger.get_logger())
