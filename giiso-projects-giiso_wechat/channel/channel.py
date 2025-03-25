"""
Message sending channel abstract class
"""
import os
import threading

from base.func_giiso import Giiso
from channel.reply import *
from job_mgmt import Job
from configuration import config
import requests
import time
import sys
from logger import logger

class Channel(Job):
    channel_type = ""
    user_id = ""
    NOT_SUPPORT_REPLYTYPE = [ReplyType.VOICE, ReplyType.IMAGE]

    def __init__(self):
        super().__init__()
        self._inited = False
        self.chat:Giiso = None
        self.user_id = None
        self.name = None
        self.key_words = []
        self.fileReply = "0"#是否开启文件回复,0:关闭,1:开启
        self.imageRec = "0"#是否开启图片识别,0:关闭,1:开启
        self.roleName = "通用助手"
        self.message_count = {}
        self.max_messages = 10
        self.lock = threading.Lock()  # 用于线程同步

    @property
    def inited(self):
        with self.lock:  # 读取状态时加锁，保证线程安全
            return self._inited

    @inited.setter
    def inited(self, value):
        with self.lock:  # 修改状态时加锁
            self._inited = value

    def startup(self):
        """
        init channel
        """
        raise NotImplementedError

    def get_user_info(self):
        """
        get user info
        """
        raise NotImplementedError

    def cleanup(self) -> None:
        """
        cleanup
        """
        raise NotImplementedError

    def send_text(self, text: str, receiver: str) -> bool:
        """
        send text
        """
        raise NotImplementedError

    def send_image(self, path: str, receiver: str) -> bool:
        """
        send image
        """
        raise NotImplementedError

    def init_bot(self):
        url = config.Giiso.get("base_url") + "/app/client/detail"
        payload = {
            "wxuin": self.user_id
        }

        # 定义轮询的最大次数，防止死循环
        max_retries = 150
        retries = 0

        while retries < max_retries:
            response = requests.post(url, json=payload)
            data = response.json()
            logger.info(f"获取到当前智能体配置信息：{data}")
            # 检查code是否为0
            if data.get("code") == "0":  # 确保code是字符串"0"
                self.key_words = data.get("data", {}).get("keywords")
                self.fileReply = data.get("data", {}).get("fileReply")
                self.imageRec = data.get("data", {}).get("imageRec")
                self.roleName = data.get("data", {}).get("roleName")
                # self.black_list = self.fetch_black_list()
                return True
            else:
                logger.info(f"尝试 {retries + 1}/{max_retries}，等待 10 秒后重试...")

            # 等待3秒后再次发送请求
            retries += 1
            time.sleep(10)
        logger.info("超过最大重试次数，未能成功获取数据")
        sys.exit("程序已关闭")

    def keepRunningAndBlockProcess(self):
        """
                保持机器人运行，不让进程退出
        """
        try:
            while True:
                self.runPendingJobs()
                time.sleep(1)
        except KeyboardInterrupt:
            self.cleanup()
            # ntwork.exit_()
            os._exit(0)

