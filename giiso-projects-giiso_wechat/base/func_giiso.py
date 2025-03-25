#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import time
from typing import Callable
import requests
from configuration import config
from logger import logger


class Giiso():
    def __init__(self, user_id) -> None:
        self.base_url = config.Giiso.get("base_url")
        self.wxid= user_id
    def __repr__(self):
        return 'Giiso'

    @staticmethod
    def value_check(conf: dict) -> bool:
        if conf:
            if conf.get("base_url"):
                return True
        return False

    def get_answer(self, send_image: Callable, question: str, sender: str, wxname='', is_group=False) -> str:
        
        response = self.get_chat(query=question,wxname=wxname,is_group=is_group,receiver_wxid=sender)
        match = re.search(r'\{.*?\}', response, re.DOTALL)
        response_dict = None
        # 提取匹配到的 JSON 部分
        if match:
            json_str = match.group(0)
            response_dict = extract_and_parse_json(json_str)
            if response_dict:
                if(response_dict['type']=='image_request'):
                    img_path = f'output/picture/{self.wxid}/'
                    create_user_folder(img_path)
                    img_save_path = img_path + str(
                        time.time()).replace('.', '') + '.jpg'
                    to_text2img_str = response_dict['content']
                    if self.get_text2img(to_text2img_str, img_save_path, wxname, is_group):
                        rsp = send_image(path=os.path.join(os.getcwd(),img_save_path), receiver=sender)
                        # logger.info(rsp)
                        if rsp:
                            response = "当前绘画指令已完成。{}".format(to_text2img_str)
                        else:
                            logger.info("图像发送失败")
                            response = "图像发送失败。"
                    else:
                        response = "不好意思，当前绘图功能正在更新。"
                elif(response_dict['type']=='search_request'):
                    pass
                    # query_key = response_dict['content']
                    # query_content = find(query_key)
                    # final_query = "[检索反馈内容]"+query_content+'\n请结合以上内容回答用户的问题\n[用户问题]'+query
                    # response = self.get_chat(query=final_query,wxname=wxname,group_name=group_name, receiver_wxid=sender)
        return response
    
    def get_img_answer(self, img_path: str, from_user_id: str, from_user_nickname: str) -> str:
        if not img_path:
            return None
        # 获取图像描述
        img_text = self.get_img2text(img_path, from_user_nickname, 1)
        if not img_text:
            return None
        response = self.get_chat(query=img_text, wxname=from_user_nickname, is_group=False,
                                 receiver_wxid=from_user_id)
        return response
    
    def get_voice_answer(self, audio_path: str, from_user_id: str, from_user_nickname: str) -> str:
        if not audio_path:
            return None
        # 获取语音识别结果
        voice_text = self.get_audio2text(audio_path, self.wxid, from_user_nickname, 1, from_user_id)
        if not voice_text:
            return None
        response = self.get_chat(query=voice_text, wxname=from_user_nickname, is_group=False,
                                 receiver_wxid=from_user_id)
        return response
        
    def get_file(self, query: str, from_user_id: str, from_user_nickname: str, is_group=False):
        def file_match(keyword: str):
            try:
                headers = {
                    "Content-Type": "application/json"
                }

                data = {
                    "keyword": keyword,
                    "wxname": from_user_nickname,
                    "receiver_wxid": from_user_id,
                    "chatType": "2" if is_group else "1",
                    "wxuin": self.wxid
                }

                # 发送 POST 请求
                url = self.base_url + '/fileHelper/fileMatch'
                response = requests.post(url, headers=headers, json=data, timeout=60)

                # 检查请求是否成功
                if response.status_code == 200:
                    rsp = response.json()
                    code = rsp.get('code')
                    data = rsp.get("data")

                    if code == 0 and data:  # 如果任务成功完成并且有结果
                        return data
                    else:
                        logger.error('file match failed.')
                        return None
                else:
                    logger.info(f"file_match接口请求失败: {response.status_code}, {response.text}")
                    return None
            except Exception as e:
                logger.error(f"file_match接口请求过程中发生错误: {e}")
                return None
        try:
            result = file_match(query)
            if not result or not result.get("file_url"):
                logger.info(f"query:{query} 未匹配到文件库中的相关文件")
                return None
            logger.info(f"匹配到文件库中的相关文件，file_ulr: {result['file_url']}, answer: {result['answer']}")
            return result
        except Exception as e:
            logger.error(f"文件下载或发送失败: {e}")
            return None
    
    def get_chat(self,query, fileReply=False,reply_decisison=False,wxname='', is_group=False, receiver_wxid=''):

        # 模型调用
        def get_server_chat(prompt,fileReply=False,reply_decisison=False,wxname='',is_group=False, receiver_wxid=''):
            messages = [{"role": "user", "content": prompt}]
            # nickName=None
            if is_group:
                chatType = "2"
                # nickName = group_name
            else:
                chatType = "1"
                # nickName = wxname
            # 定义请求数据
            data = {
                "model": "",
                "chatId": 0,
                "wxuin": self.wxid,
                "chatType":chatType, #  1：表示私聊 2:表示群聊
                "wxname":wxname, # 聊天对象的微信昵称，私聊时为对方昵称，群聊时为群聊名称
                "receiver_wxid": receiver_wxid, # 聊天对象的微信id，私聊时为对方id，群聊时为群聊id
                "replyDecisison": reply_decisison,
                "fileReply": fileReply, # 1表示打开文件问答功能 0其他表示未打开文件对话功能
                "messages": messages
            }
            logger.info(data)
            try:
                url = self.base_url + '/chat/dialogue'
                response = requests.post(url, json=data, timeout=600)
                response.raise_for_status()  # 检查请求是否成功
                json_data = response.json()  # 解析JSON响应
                logger.info(json_data)
                # 输出模型的回复
                return json_data["data"]["choices"][0]["message"]["content"].strip().replace("**","")
            except requests.exceptions.RequestException as e:
                logger.error(f"请求失败: {e}")
            except KeyError:
                logger.error("响应中未找到预期的数据%s",json_data)
        
        # 获取大模型结果
        count = 6
        while count > 0:
            try:
                if len(query) > 0:
                    response = get_server_chat(query,fileReply,reply_decisison,wxname,is_group, receiver_wxid)
                    if response and len(response) > 0:
                        return response
                    else:
                        count = count - 1
            except Exception as e:
                logger.error("错误%s",e)
                count = count - 1
                time.sleep(10)
        return None

    

    ###########画图接口######################            
    def get_text2img(self, prompt, image_path, wxname, is_group):
        def wait_for_task_completion(job_id, image_path):
            while True:
                url = self.base_url + '/text2img/detail'  # 替换为实际的任务状态查询API端点
                response = requests.post(url, json={"jobId": job_id})

                if response.status_code == 200:
                    rsp = response.json()
                    logger.info(f"Task status check response: {rsp}")

                    data = rsp.get("data", {})
                    status = data.get('status')
                    result = data.get('result', [])

                    if status == 2 and result:  # 如果任务成功完成并且有结果
                        for index, item in enumerate(result, start=1):
                            if not item.get('isViolating'):  # 检查是否违规
                                image_url = item['imageUrl']
                                download_image(image_url, image_path)
                            else:
                                logger.warning(f'Image {index} is violating rules and will be skipped.')
                                return False
                        return True
                    elif status == -1:
                        logger.error('Image synthesis failed.')
                        return False
                else:
                    logger.error(f'Task status check failed, status_code: {response.status_code}')
                    return False

                time.sleep(1)  # 等待一段时间后再检查任务状态

        def download_image(image_url, image_path):
            response = requests.get(image_url)

            if response.status_code == 200:
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f'Image saved to {image_path}')
            else:
                logger.error(f'Failed to download image from {image_url}, status_code: {response.status_code}')
                
                
        url = self.base_url + '/text2img/submit'  # 替换为实际的任务创建API端点
        chat_type = "2" if is_group else "1"

        payload = {
            "ratio": "1",
            "wxname": wxname,# 聊天对象的微信昵称
            "chatType": chat_type,
            "prompt": prompt,
            "wxuin": self.wxid,#托管者的微信id
        }

        response = requests.post(url, json=payload)

        if response.status_code == 200:
            rsp = response.json()
            logger.info(f"Task creation response: {rsp}")
            
            if rsp['code'] == "0":
                job_id = rsp.get('data', {}).get('jobId')
                status = rsp.get('data', {}).get('status')

                if not job_id or status == "-1":
                    logger.error('Failed to get jobId from the server.')
                    return False

                # 等待任务完成
                if wait_for_task_completion(job_id, image_path):
                    logger.info('All images have been successfully downloaded.')
                    return True
                else:
                    logger.error('Failed to complete task or download images.')
                    return False
            else:
                return False
        else:
            logger.error(f'Task creation failed, status_code: {response.status_code}')
            return False

    

    # get_text2img('一只小狗', 'output/picture/人/'+str(
    #                 time.time()).replace('.', '') + '.jpg',"3327135513",'再会',None)

    ###########画图接口######################

    ##########语音转文本接口################
    def get_audio2text(self,file_path, user_uin, wxname, chat_type, receiver_wxid):
        """
        创建语音转文本任务，并轮询获取任务结果。
        :param file_path: 语音文件路径
        :param user_uin: 机器人绑定微信的wxuin
        :param wxname: 与机器人对话对象的微信昵称
        :param chat_type: 对话类型（1-单聊，2-群聊）
        :return: 任务结果（文本）或 False
        """
        create_url = self.base_url + '/audio2text/submit'
        detail_url = self.base_url + '/audio2text/detail'

        # 构建 FormData
        files = {
            'file': (file_path.split('/')[-1], open(file_path, 'rb'), 'audio/mp3')
        }
        data = {
            'wxuin': user_uin,
            'wxname': wxname,
            "receiver_wxid": receiver_wxid,  # 聊天对象的微信id
            'chatType': str(chat_type)
        }

        try:
            # 创建任务
            response = requests.post(create_url, data=data, files=files)
            if response.status_code == 200:
                rsp = response.json()
                logger.info(f"Task creation response: {rsp}")

                if rsp['code'] == "0":
                    job_id = rsp['data'].get('jobId')

                    if not job_id:
                        logger.error('Failed to get jobId from the server.')
                        return False

                    # 轮询任务结果
                    while True:
                        result_response = requests.post(detail_url, json={"jobId": job_id})
                        if result_response.status_code == 200:
                            result_rsp = result_response.json()
                            logger.info(f"Task status response: {result_rsp}")

                            result_status = result_rsp['data'].get('status')
                            result_text = result_rsp['data'].get('result')

                            if result_status == 2 and result_text:
                                return result_text
                            elif result_status == -1:
                                logger.error("Task failed.")
                                return False
                        else:
                            logger.error(f"Failed to fetch task status, status_code: {result_response.status_code}")
                            return False

                        time.sleep(1)  # 等待一段时间后再次检查任务状态
                else:
                    logger.error(f"Task creation failed: {rsp['msg']}")
                    return False
            else:
                logger.error(f"Task creation failed, status_code: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
        
    def get_img2text(self,file_path, wxname, chat_type):
        """
        创建图片转文本任务，并轮询获取任务结果。
        :param file_path: 图片文件路径
        :param user_uin: 机器人绑定微信的wxuin
        :param wxname: 与机器人对话对象的微信昵称
        :param chat_type: 对话类型（1-单聊，2-群聊）
        :return: 任务结果（文本）或 False
        """
        create_url = self.base_url + '/img2text/submit'
        detail_url = self.base_url + '/img2text/detail'

        # 构建 FormData
        files = {
            'file': (file_path.split('/')[-1], open(file_path, 'rb'), 'image/png')
        }
        data = {
            'wxuin': self.wxid,
            'wxname': wxname,
            'chatType': str(chat_type)
        }

        try:
            # 创建任务
            response = requests.post(create_url, data=data, files=files)
            if response.status_code == 200:
                rsp = response.json()
                logger.info(f"Task creation response: {rsp}")

                if rsp['code'] == "0":
                    job_id = rsp['data'].get('jobId')

                    if not job_id:
                        logger.error('Failed to get jobId from the server.')
                        return False

                    # 轮询任务结果
                    while True:
                        result_response = requests.post(detail_url, json={"jobId": job_id})
                        if result_response.status_code == 200:
                            result_rsp = result_response.json()
                            logger.info(f"Task status response: {result_rsp}")

                            result_status = result_rsp['data'].get('status')
                            result_text = result_rsp['data'].get('result')

                            if result_status == 2 and result_text:
                                return result_text
                            elif result_status == -1:
                                logger.error("Task failed.")
                                return False
                        else:
                            logger.error(f"Failed to fetch task status, status_code: {result_response.status_code}")
                            return False

                        time.sleep(1)  # 等待一段时间后再次检查任务状态
                else:
                    logger.error(f"Task creation failed: {rsp['msg']}")
                    return False
            else:
                logger.error(f"Task creation failed, status_code: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
        
    # def getIdName(wcf, Id):
    #     """
    #     获取好友或者群聊昵称
    #     :return:
    #     """
    #     try:
    #         name_list = wcf.query_sql("MicroMsg.db",
    #                                 f"SELECT UserName, NickName FROM Contact WHERE UserName = '{Id}';")
    #         if not name_list:
    #             return getIdName(wcf, Id)
    #         name = name_list[0]['NickName']
    #         return name
    #     except Exception as e:
    #         op(f'[~]: 获取好友或者群聊昵称出现错误, 错误信息: {e}')
    #         return getIdName(wcf, Id)

# 创建输出文件夹
def create_user_folder(output_file):
    if not os.path.exists(output_file):
        os.makedirs(output_file)
        
# 尝试直接校验
def extract_and_parse_json(response):
    try:
        # 尝试将匹配的内容解析为 JSON
        response_dict = json.loads(response)
        return response_dict  # 返回第一个有效的 JSON 数据
    except json.JSONDecodeError:  
        logger.error("No valid JSON found in the response.")
    return None   

if __name__ == "__main__":
    from configuration import Config
    # config = Config().CHATGPT
    # if not config:
    #     exit(0)
    #
    # chat = ChatGPT(config)
    #
    # while True:
    #     q = input(">>> ")
    #     try:
    #         time_start = datetime.now()  # 记录开始时间
    #         print(chat.get_answer(q, "wxid"))
    #         time_end = datetime.now()  # 记录结束时间
    #
    #         print(f"{round((time_end - time_start).total_seconds(), 2)}s")  # 计算的时间差为程序的执行时间，单位为秒/s
    #     except Exception as e:
    #         print(e)
