# -*- coding: utf-8 -*-

import time
from typing import Any, Callable

import schedule

from task import SalesMessageTask


class Job(object):
    def __init__(self) -> None:
        pass

    def onEverySeconds(self, seconds: int, task: Callable[..., Any], *args, **kwargs) -> None:
        """
        每 seconds 秒执行
        :param seconds: 间隔，秒
        :param task: 定时执行的方法
        :return: None
        """
        schedule.every(seconds).seconds.do(task, *args, **kwargs)

    def onEveryMinutes(self, minutes: int, task: Callable[..., Any], *args, **kwargs) -> None:
        """
        每 minutes 分钟执行
        :param minutes: 间隔，分钟
        :param task: 定时执行的方法
        :return: None
        """
        schedule.every(minutes).minutes.do(task, *args, **kwargs)

    def onEveryHours(self, hours: int, task: Callable[..., Any], *args, **kwargs) -> None:
        """
        每 hours 小时执行
        :param hours: 间隔，小时
        :param task: 定时执行的方法
        :return: None
        """
        schedule.every(hours).hours.do(task, *args, **kwargs)

    def onEveryDays(self, days: int, task: Callable[..., Any], *args, **kwargs) -> None:
        """
        每 days 天执行
        :param days: 间隔，天
        :param task: 定时执行的方法
        :return: None
        """
        schedule.every(days).days.do(task, *args, **kwargs)

    def onEveryTime(self, times: int, task: Callable[..., Any], *args, **kwargs) -> None:
        """
        每天定时执行
        :param times: 时间字符串列表，格式:
            - For daily jobs -> HH:MM:SS or HH:MM
            - For hourly jobs -> MM:SS or :MM
            - For minute jobs -> :SS
        :param task: 定时执行的方法
        :return: None

        例子: times=["10:30", "10:45", "11:00"]
        """
        if not isinstance(times, list):
            times = [times]

        for t in times:
            schedule.every(1).days.at(t).do(task, *args, **kwargs)

    def runPendingJobs(self) -> None:
        schedule.run_pending()


class Bot:

    def __init__(self):
        pass

    def sendTextMsg(self, msg: str, receiver: str, at_list: str = "", is_send_now: bool = False) -> None:
        print(f"发送消息: {msg}")

class Task:

    def __init__(self):
        pass

    def run(self, sendTextMsg: Callable[..., Any]):
        sendTextMsg("hello", "filehelper")

if __name__ == "__main__":
    def printStr(s):
        print(s)
    #
    # Bot = Bot()
    # Task = SalesMessageTask("wxid_2lc86s4dvk0x22")

    job = Job()
    # job.onEverySeconds(60, Task.run, Bot.sendTextMsg)
    job.onEveryMinutes(59, printStr, "onEveryMinutes 59")
    # job.onEveryHours(23, printStr, "onEveryHours 23")
    # job.onEveryDays(1, printStr, "onEveryDays 1")
    # job.onEveryTime("23:59", printStr, "onEveryTime 23:59")

    while True:
        job.runPendingJobs()
        time.sleep(1)
