"""
channel factory
"""
from .channel import Channel


def create_channel(channel_type) -> Channel:
    """
    create a channel instance
    :param channel_type: channel type code
    :return: channel instance
    """
    ch = Channel()
    if channel_type == "wechat":
        from channel.wechat.wechat_channel import WeChatChannel
        ch = WeChatChannel()
    elif channel_type == "wework":
        from channel.wework.wework_channel import WeworkChannel
        ch = WeworkChannel()
    else:
        raise RuntimeError
    ch.channel_type = channel_type
    return ch