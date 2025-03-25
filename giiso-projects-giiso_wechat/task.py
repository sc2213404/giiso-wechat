import asyncio
import heapq
import threading
import time
from typing import Callable, Any
import requests
from configuration import config
from logger import logger
import random


class DelayTimeProvider:
    def __init__(self):
        # 初始化延时时间数组
        self.initialize_array()

    def initialize_array(self):
        # 生成 30, 60, 90, ..., 3600 的延迟时间序列
        self.array = [i for i in range(30, 3601, 30)]
        # self.array = [i for i in range(1, 10, 1)]
        # 打乱数组
        random.shuffle(self.array)

    def get_delay(self):
        # 如果数组为空，重新初始化
        if not self.array:
            self.initialize_array()

        # 获取并移除数组中的第一个延迟时间
        return self.array.pop(0)


def can_send_sales_message(wxuin: str, receiver_wxid: str):
    """
    判断该用户是否满足发送主动销售消息的条件
    """
    try:
        headers = {
            "Content-Type": "application/json"
        }

        data = {
            "wxuin": wxuin,
            "receiver_wxid": receiver_wxid
        }

        # 发送 POST 请求
        url = config.Giiso.get('base_url') + '/activeChatMsg/sendCheck'
        response = requests.post(url, headers=headers, json=data)

        # 检查请求是否成功
        if response.status_code == 200:
            rsp = response.json()
            code = rsp.get('code')
            data = rsp.get("data")

            if code == '0':  # 如果任务成功完成并且有结果
                return 'send' in data and data['send'] == '1'
            else:
                logger.error('/activeChatMsg/sendCheck接口返回数据异常: ' + str(rsp))
                return False
        else:
            logger.info(f"/activeChatMsg/sendCheck接口请求失败: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        logger.error(f"/activeChatMsg/sendCheck接口请求过程中发生错误: {e}")
        return False


class DelayTaskScheduler:
    def __init__(self, wxuin: str):
        self.tasks = []
        self.wxuin = wxuin
        self.lock = threading.Lock()

    def add_task(self, delay, task, *args, **kwargs):
        # 将任务延时和任务本身打包，按延时排序
        heapq.heappush(self.tasks, (time.time() + delay, task, args, kwargs))

    def run(self):
        while True:
            try:
                time.sleep(1)  # 每秒检查一次
                with self.lock:
                    current_time = time.time()
                    # 执行到期的任务
                    while self.tasks and self.tasks[0][0] <= current_time:
                        _, task, args, kwargs = heapq.heappop(self.tasks)
                        receiver_wxid = args[1]
                        if receiver_wxid is None:
                            logger.warning("未找到 receiver_wxid，跳过任务执行")
                            continue
                        if not can_send_sales_message(self.wxuin, receiver_wxid):
                            logger.info(f"用户{receiver_wxid}未满足发送主动销售消息的条件，跳过发送")
                            continue
                        task(*args, **kwargs)  # 解包参数并调用任务
            except Exception as e:
                logger.error(f"主动销售消息队列的任务调度器出错：{e}")
                # 可以选择在这里进行一些错误恢复或记录日志操作


class SalesMessageTask:
    """
    主动销售定时发送消息任务
    """

    sales_message_prompt = "根据历史记录判断用户对什么产品感兴趣，如果都不感兴趣，向用户开启问候并推销知识库中的产品。你需要称呼客户为:{user_nickname}"

    def __init__(self, wxuin: str):
        self.wxuin = wxuin
        # 创建消息调度器
        self.scheduler = DelayTaskScheduler(wxuin)
        # 启动任务调度
        threading.Thread(target=self.scheduler.run, daemon=True).start()

    def run(self, sendTextMsg: Callable[..., Any]):
        try:
            logger.info("------------开始执行主动销售定时发送消息任务-------------")
            # 1. 从服务端接口拉取需要主动销售发送营销消息的用户列表
            user_list = self.pull_sales_user_list()
            if not user_list:
                logger.info("------------当前无需发送-------------")
                return

            delay_provider = DelayTimeProvider()

            # 2. 逐个用户发送消息
            for user in user_list:
                receiver_wxid = user.get('wxuin')  # 对话者的微信id
                user_nickname = user.get('nickname')  # 发送消息时，对接收方的称谓
                user_wxname = user.get('wxname')  # 对话者的微信名称
                content = user.get('content')  # 消息内容

                # 如果没有自定义消息，则根据历史记录判断用户对什么产品感兴趣
                if not content:
                    content = self.get_sales_message(receiver_wxid, user_wxname, user_nickname)
                if not content:
                    continue

                # 添加延时发送消息任务
                delay_time = delay_provider.get_delay()
                self.scheduler.add_task(delay_time, sendTextMsg, content, receiver_wxid)
                # sendTextMsg(content, receiver_wxid, '', False)
                logger.info(
                    f"对用户：{receiver_wxid} 的主动销售消息已添加进消息队列，延时{delay_time}s后发送，消息内容为: {content}")
        except Exception as e:
            logger.error(f"主动销售消息任务执行出错: {e}")

    def pull_sales_user_list(self):
        """
        从服务端接口拉取主动销售的用户列表
        """
        # return [{"wxuin": "wxid_2lc86s4dvk0x22", "nickname": "张三a", "wxname": "张三a", "content": "你好，A"},
        #         {"wxuin": "wxid_2lc86s4dvk0x22", "nickname": "张三b", "wxname": "张三b", "content": "你好，B"},
        #         {"wxuin": "wxid_2lc86s4dvk0x22", "nickname": "张三c", "wxname": "张三c", "content": "你好，C"},
        #         {"wxuin": "wxid_2lc86s4dvk0x22", "nickname": "张三d", "wxname": "张三d", "content": "你好，D"},
        #         {"wxuin": "wxid_2lc86s4dvk0x22", "nickname": "张三e", "wxname": "张三e", "content": "你好，E"}]
        try:
            headers = {
                "Content-Type": "application/json"
            }

            data = {
                "wxuin": self.wxuin
            }

            # 发送 POST 请求
            url = config.Giiso.get('base_url') + '/activeChatMsg/list'
            response = requests.post(url, headers=headers, json=data)

            # 检查请求是否成功
            if response.status_code == 200:
                rsp = response.json()
                code = rsp.get('code')
                data = rsp.get("data")
                default_prompt = rsp.get("defaultPrompt")
                if default_prompt:
                    self.sales_message_prompt = default_prompt

                if code == '0':  # 如果任务成功完成并且有结果
                    return data
                else:
                    logger.error('/activeChatMsg/list接口返回数据异常: ' + str(rsp))
                    return None
            else:
                logger.info(f"/activeChatMsg/list接口请求失败: {response.status_code}, {response.text}")
                return None
        except Exception as e:
            logger.error(f"/activeChatMsg/list接口请求过程中发生错误: {e}")
            return None

    def get_sales_message(self, receiver_wxid, user_wxname, user_nickname):
        """
        从服务端接口拉取主动销售消息
        """
        content = self.sales_message_prompt.replace("{user_nickname}", user_nickname)
        # prompt = f"根据历史记录判断用户对什么产品感兴趣，如果都不感兴趣，向用户开启问候并推销知识库中的产品。你需要称呼客户为:{user_nickname}"
        messages = [{"role": "user", "content": content}]
        # 定义请求数据
        data = {
            "model": "",
            "chatId": 0,
            "wxuin": self.wxuin,
            "chatType": "0",  # 0:表示主动销售聊天 1：表示私聊 2:表示群聊
            "wxname": user_wxname,  # 聊天对象的微信昵称
            "receiver_wxid": receiver_wxid,  # 聊天对象的微信id
            "replyDecisison": False,
            "fileReply": False,  # 1表示打开文件问答功能 0其他表示未打开文件对话功能
            "messages": messages
        }
        logger.info(data)
        try:
            url = config.Giiso.get('base_url') + '/chat/dialogue'
            response = requests.post(url, json=data, timeout=600)
            response.raise_for_status()  # 检查请求是否成功
            json_data = response.json()  # 解析JSON响应
            logger.info(json_data)
            # 输出模型的回复
            return json_data["data"]["choices"][0]["message"]["content"].strip().replace("**", "")
        except Exception as e:
            logger.error(f"get_sales_message请求失败: {e}")


if __name__ == '__main__':
    # SalesMessageTask("wxid_2lc86s4dvk0x22").run(
    #     lambda msg, receiver, at_list, is_send_now: logger.info(f"发送消息: {msg}"))

    # print(can_send_sales_message("wxid_2lc86s4dvk0x22", 'zongbin2504'))

    prompt = "根据历史记录判断用户对什么产品感兴趣，如果都不感兴趣，向用户开启问候并推销知识库中的产品。你需要称呼客户为:{user_nickname}"
    print(prompt.replace("{user_nickname}", "张三"))