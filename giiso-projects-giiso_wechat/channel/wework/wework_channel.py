import os
import random
import threading

from base.func_giiso import Giiso
from task import SalesMessageTask

os.environ['ntwork_LOG'] = "ERROR"
import ntwork

# 手动设置 WeWork 路径和版本
wework_mgr = ntwork.WeWorkMgr()
wework_mgr.set_wework_exe_path("C:\\Program Files (x86)\\Tencent\\WeChat\\WeChat.exe", "3.9.11")


from channel.wework.wework_message import *
from channel.wework.wework_message import WeworkMessage
from channel.common.singleton import singleton
from logger import logger
from channel.common.utils import download_file

wework = ntwork.WeWork()

def get_wxid_by_name(room_members, group_wxid, name):
    if group_wxid in room_members:
        for member in room_members[group_wxid]['member_list']:
            if member['room_nickname'] == name or member['username'] == name:
                return member['user_id']
    return None  # 如果没有找到对应的group_wxid或name，则返回None


# def download_and_compress_image(url, filename, quality=30):
#     # 确定保存图片的目录
#     directory = os.path.join(os.getcwd(), "tmp")
#     # 如果目录不存在，则创建目录
#     if not os.path.exists(directory):
#         os.makedirs(directory)
#
#     # 下载图片
#     pic_res = requests.get(url, stream=True)
#     image_storage = io.BytesIO()
#     for block in pic_res.iter_content(1024):
#         image_storage.write(block)
#
#     # 检查图片大小并可能进行压缩
#     sz = fsize(image_storage)
#     if sz >= 10 * 1024 * 1024:  # 如果图片大于 10 MB
#         logger.info("[wework] image too large, ready to compress, sz={}".format(sz))
#         image_storage = compress_imgfile(image_storage, 10 * 1024 * 1024 - 1)
#         logger.info("[wework] image compressed, sz={}".format(fsize(image_storage)))
#
#     # 将内存缓冲区的指针重置到起始位置
#     image_storage.seek(0)
#
#     # 读取并保存图片
#     image = Image.open(image_storage)
#     image_path = os.path.join(directory, f"{filename}.png")
#     image.save(image_path, "png")
#
#     return image_path


# def download_video(url, filename):
#     # 确定保存视频的目录
#     directory = os.path.join(os.getcwd(), "tmp")
#     # 如果目录不存在，则创建目录
#     if not os.path.exists(directory):
#         os.makedirs(directory)
#
#     # 下载视频
#     response = requests.get(url, stream=True)
#     total_size = 0
#
#     video_path = os.path.join(directory, f"{filename}.mp4")
#
#     with open(video_path, 'wb') as f:
#         for block in response.iter_content(1024):
#             total_size += len(block)
#
#             # 如果视频的总大小超过30MB (30 * 1024 * 1024 bytes)，则停止下载并返回
#             if total_size > 30 * 1024 * 1024:
#                 logger.info("[WX] Video is larger than 30MB, skipping...")
#                 return None
#
#             f.write(block)
#
#     return video_path


def create_message(wework_instance, message, is_group):
    logger.debug(f"正在为{'群聊' if is_group else '单聊'}创建 WeworkMessage")
    cmsg = WeworkMessage(message, wework=wework_instance, channel= WeworkChannel(), is_group=is_group)
    logger.debug(f"cmsg:{cmsg}")
    return cmsg


def handle_message(cmsg, is_group):
    logger.debug(f"准备用 WeworkChannel 处理{'群聊' if is_group else '单聊'}消息")
    if is_group:
        handle_group(cmsg)
    else:
        handle_single(cmsg)
    logger.debug(f"已用 WeworkChannel 处理完{'群聊' if is_group else '单聊'}消息")


def handle_single(msg: WeworkMessage):
    if msg.from_user_id == msg.to_user_id:
        # ignore self reply
        return
    if msg.ctype == ContextType.VOICE:
        logger.debug("[WX]receive voice msg: {}".format(msg.content))
        msg.prepare()
        rsp = msg.channel.chat.get_voice_answer(msg.content, msg.from_user_id, msg.from_user_nickname)
        if rsp:
            wework.send_text(msg.other_user_id, rsp)
    elif msg.ctype == ContextType.IMAGE and (msg.channel.imageRec == '1'):
        logger.debug("[WX]receive image msg: {}".format(msg.content))
        msg.prepare()
        rsp = msg.channel.chat.get_img_answer(msg.content, msg.from_user_id, msg.from_user_nickname)
        if rsp:
            wework.send_text(msg.other_user_id, rsp)
    elif msg.ctype == ContextType.PATPAT:
        logger.debug("[WX]receive patpat msg: {}".format(msg.content))
    elif msg.ctype == ContextType.TEXT:
        logger.debug("[WX]receive text msg: {}, cmsg={}".format(json.dumps(msg._rawmsg, ensure_ascii=False), msg))
        toChitchat(msg)
    else:
        logger.debug("[WX]receive msg: {}, cmsg={}".format(msg.content, msg))


def handle_group(msg: WeworkMessage):
    # 群聊消息只处理文本消息
    if msg.ctype != ContextType.TEXT:
        return
    # 被@或者有关键词，都会触发闲聊，一旦触发本轮对话会回复10次
    chat_turns_key = f"{msg.other_user_id}_{msg.actual_user_id}"
    # 被@
    if msg.is_at:
        msg.channel.message_count[chat_turns_key] = 0
        toChitchat(msg)
        return

    # 未被@，但是有关键词
    if msg.channel.key_words and any(keyword in msg.content for keyword in msg.channel.key_words):
        msg.channel.message_count[chat_turns_key] = 0
        toChitchat(msg)
        return

    if chat_turns_key in msg.channel.message_count and msg.channel.message_count[chat_turns_key] < msg.channel.max_messages:
        msg.channel.message_count[chat_turns_key] += 1
        # 根据本次消息内容判断是否有对话意图
        q = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")
        rsp = msg.channel.chat.get_chat(query=q, reply_decisison=True, wxname=msg.from_user_nickname,
                                        is_group=msg.is_group, receiver_wxid=msg.from_user_id)
        if rsp.startswith('0'):
            return
        else:
            toChitchat(msg)


def toChitchat(msg: WeworkMessage) -> bool:
    """闲聊，接入 ChatGPT
    """
    wework_channel = msg.channel
    chat: Giiso = wework_channel.chat
    if not chat:  # 没接 ChatGPT，固定回复
        return False

    q = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")
    if q == "":
        q = "你在微信中被@了，请根据最近的消息进行回复"
    else:
        # 非空消息，如果当前智能体开启了文件回复，则优先匹配文件，匹配到文件则直接回复文件、不再进行知识库回复
        if wework_channel.fileReply == '1' and file_match(chat, msg, q):
            return True

    rsp = chat.get_answer(wework_channel.send_image, q, msg.from_user_id, msg.from_user_nickname, msg.is_group)
    if not rsp:
        logger.error(f"无法从 ChatGPT 获得答案")
        return False

    if msg.is_group:
        wework.send_room_at_msg(msg.other_user_id, rsp, [msg.actual_user_id])
    else:
        wework.send_text(msg.other_user_id, rsp)

    # wework.send_link_card(msg.other_user_id,
    #                       "在奇妙大陆上经营你的动物商铺帝国——《萌不萌宠不宠》邀你打造商业传奇！",
    #                       "欢迎来到动物星球-《萌不萌宠不宠》，一个充满智慧动物与无限可能的奇幻世界！在这里，每个城市、每个国家都由不同的动物群体组成，它们有各自独特的文化和需求。",
    #                       "https://mp.weixin.qq.com/s/TcCnInAQi1QEC5ebz22Wew",
    #                       "https://mmbiz.qpic.cn/mmbiz_png/ec7anicuAye7bnbvI38F9uQVyIctSuwkxZWCqw3VwJtwFVpmxBI9ARTgAJ95PJeiaDzSm7lCIbqeeJSiaFGp7Luug/640?wx_fmt=png&amp;from=appmsg")
    return True

def file_match(chat: Giiso, msg: WeworkMessage, q:str) -> bool:
    file_match_result = chat.get_file(q, msg.from_user_id, msg.from_user_nickname, msg.is_group)
    if not file_match_result:
        return False

    file_url = file_match_result['file_url']
    if not file_url:
        return False

    answer = file_match_result['answer']
    if answer:
        if msg.is_group:
            wework.send_room_at_msg(msg.other_user_id, answer, [msg.actual_user_id])
        else:
            wework.send_text(msg.other_user_id, answer)

    save_dir = os.path.join(os.getcwd(), "output", "file", msg.channel.user_id,
                            msg.from_user_id.replace(":", ""))
    file_path = download_file(file_url, save_dir)
    wework.send_file(msg.other_user_id, file_path)
    return True

def _check(func):
    def wrapper(self, cmsg: ChatMessage):
        msgId = cmsg.msg_id
        create_time = cmsg.create_time  # 消息时间戳
        if create_time is None:
            return func(self, cmsg)
        if int(create_time) < int(time.time()) - 60:  # 跳过1分钟前的历史消息
            logger.debug("[WX]history message {} skipped".format(msgId))
            return
        return func(self, cmsg)

    return wrapper


@wework.msg_register(
    [ntwork.MT_RECV_TEXT_MSG, ntwork.MT_RECV_IMAGE_MSG, 11072, ntwork.MT_RECV_LINK_CARD_MSG, ntwork.MT_RECV_FILE_MSG,
     ntwork.MT_RECV_VOICE_MSG])
def all_msg_handler(wework_instance: ntwork.WeWork, message):
    logger.debug(f"收到消息: {message}")
    if WeworkChannel().inited and 'data' in message:
        sender = message['data'].get("sender", None)
        if sender and sender == WeworkChannel().user_id:
            logger.debug("自己发的，直接结束")
            return
        # 首先查找conversation_id，如果没有找到，则查找room_conversation_id
        conversation_id = message['data'].get('conversation_id', message['data'].get('room_conversation_id'))
        if conversation_id is not None:
            is_group = "R:" in conversation_id
            try:
                cmsg = create_message(wework_instance=wework_instance, message=message, is_group=is_group)
            except NotImplementedError as e:
                logger.error(f"[WX]{message.get('MsgId', 'unknown')} 跳过: {e}")
                return None
            delay = random.randint(1, 2)
            timer = threading.Timer(delay, handle_message, args=(cmsg, is_group))
            timer.start()
        else:
            logger.debug("消息数据中无 conversation_id")
            return None
    return None


def get_with_retry(get_func, max_retries=5, delay=5):
    retries = 0
    result = None
    while retries < max_retries:
        result = get_func()
        if result:
            break
        logger.warning(f"获取数据失败，重试第{retries + 1}次······")
        retries += 1
        time.sleep(delay)  # 等待一段时间后重试
    return result


@singleton
class WeworkChannel(Channel):
    NOT_SUPPORT_REPLYTYPE = []

    def __init__(self):
        super().__init__()

    def startup(self):
        # smart = conf().get("wework_smart", True)
        wework.open(True)
        logger.info("等待登录······")
        wework.wait_login()
        login_info = wework.get_login_info()
        self.user_id = login_info['user_id']
        self.name = login_info['nickname'] if login_info['nickname'] else login_info['username']
        logger.info(f"登录信息:>>>user_id:{self.user_id}>>>>>>>>name:{self.name}")
        logger.info("静默延迟20s，等待客户端刷新数据，请勿进行任何操作······")
        time.sleep(20)
        contacts = get_with_retry(wework.get_external_contacts)
        rooms = get_with_retry(wework.get_rooms)
        directory = os.path.join(os.getcwd(), "output", "json", self.user_id)
        if not contacts or not rooms:
            logger.error("获取contacts或rooms失败，程序退出")
            ntwork.exit_()
            os.exit(0)
        if not os.path.exists(directory):
            os.makedirs(directory)
        # 将contacts保存到json文件中
        with open(os.path.join(directory, 'wework_contacts.json'), 'w', encoding='utf-8') as f:
            json.dump(contacts, f, ensure_ascii=False, indent=4)
        with open(os.path.join(directory, 'wework_rooms.json'), 'w', encoding='utf-8') as f:
            json.dump(rooms, f, ensure_ascii=False, indent=4)
        # 创建一个空字典来保存结果
        result = {}

        # 遍历列表中的每个字典
        for room in rooms['room_list']:
            # 获取聊天室ID
            room_wxid = room['conversation_id']

            # 获取聊天室成员
            room_members = wework.get_room_members(room_wxid)

            # 将聊天室成员保存到结果字典中
            result[room_wxid] = room_members

        # 将结果保存到json文件中
        with open(os.path.join(directory, 'wework_room_members.json'), 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        self.chat = Giiso(self.user_id)
        self.init_bot()

        # 给机器人添加主动销售定时任务，每 5 分钟执行一次
        sales_message_task = SalesMessageTask(self.user_id)
        self.onEverySeconds(300, sales_message_task.run, self.send_text)

        logger.info("wework程序初始化完成········")
        self.inited = True
        self.keepRunningAndBlockProcess()

    def get_user_info(self):
        login_info = wework.get_login_info()
        if not login_info or not login_info['user_id']:
            logger.error("企业微信未登录，用户信息获取失败")
            return None
        user_id = login_info['user_id']
        name = login_info['nickname'] if login_info['nickname'] else login_info['username']
        return {'wxid': user_id, 'name': name}

    def send_text(self, text: str, receiver: str) -> bool:
        return wework.send_text(receiver, text)

    def send_image(self, path: str, receiver: str) -> bool:
        return wework.send_image(receiver, path)

    def cleanup(self) -> None:
        ntwork.exit_()
        # wework.on_close()
