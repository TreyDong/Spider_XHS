# encoding: utf-8
import json
import re
import urllib
import requests
from xhs_utils.xhs_util import splice_str, generate_request_params, generate_x_b3_traceid, get_common_headers
from loguru import logger
import time
from datetime import datetime, timedelta

"""
    获小红书的api
    :param cookies_str: 你的cookies
"""
class Creator_Apis():
    def __init__(self):
        self.base_url = "https://creator.xiaohongshu.com"


    def get_note_data_detail(self,cookies_str, note_id:str):
        res_json = None
        try:
            api = '/api/galaxy/creator/datacenter/note/base?note_id={}'.format(note_id)
            headers, cookies, data = generate_request_params(cookies_str, api)
            response = requests.get(self.base_url + api, headers=headers, cookies=cookies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json


    def get_note_data(self, cookies_str: str, post_begin_date: datetime = None, post_end_date: datetime = None, type: int = 0, page_size: int = 10, page_num: int = 1):
        """
        https://creator.xiaohongshu.com/api
        /galaxy/creator/datacenter/note/analyze/list
        :param post_begin_date: 开始日期，默认为上一周的日期
        :param post_end_date: 结束日期，默认为当前日期
        :param type: 类型，默认为 0
        :param page_size: 每页数量，默认为 10
        :param page_num: 页码，默认为 1
        :return:
        """
        res_json = None
        try:
            if post_begin_date is None:
                post_begin_date = datetime.now() - timedelta(days=7)
            if post_end_date is None:
                post_end_date = datetime.now()
            
            post_begin_time = int(post_begin_date.timestamp() * 1000)
            post_end_time = int(post_end_date.timestamp() * 1000)
            
            api = f"/api/galaxy/creator/datacenter/note/analyze/list?post_begin_time={post_begin_time}&post_end_time={post_end_time}&type={type}&page_size={page_size}&page_num={page_num}"
            headers, cookies, data = generate_request_params(cookies_str, api)
            response = requests.get(self.base_url + api, headers=headers, cookies=cookies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

if __name__ == '__main__':
    """
        此文件为小红书api的使用示例
        所有涉及数据爬取的api都在此文件中
        数据注入的api违规请勿尝试
    """
    xhs_apis = Creator_Apis()
    cookies_str = r'a1=1965d4add07x1q6lgtjn8v3a8ehh6aei5pr8u270t30000262724; webId=2db11ff5865d401a604ff432046730f7; abRequestId=2db11ff5865d401a604ff432046730f7; gid=yjK2f2fW8K2fyjK2f40ffUJW8WCyAK1k9VIYF89hq0YdxYq8xK0d37888JKJWJ48SDj4iW0j; customerClientId=089030337226232; x-user-id-chengfeng.xiaohongshu.com=642f62b8000000001002b779; access-token-chengfeng.xiaohongshu.com=customer.ad_wind.AT-68c51749684719195118541667cwcyt8boj8yeyf; x-user-id-school.xiaohongshu.com=642f62b8000000001002b779; unread={%22ub%22:%22681ac08e000000002100ff09%22%2C%22ue%22:%22681b556a0000000020028a51%22%2C%22uc%22:47}; x-user-id-creator.xiaohongshu.com=6807735a000000000a03e8d0; x-user-id-ark.xiaohongshu.com=6807735a000000000a03e8d0; access-token-ark.xiaohongshu.com=customer.ark.AT-68c5175078409467241206568e1jlrh3w60aa1aa; web_session=040069b973301279b886c57d043a4b3dcc1c9a; customer-sso-sid=68c517507841101431350827qlxary4iyqz4imn5; access-token-creator.xiaohongshu.com=customer.creator.AT-68c517507841101435820311eqasgzghndqxbhgw; galaxy_creator_session_id=CCVk6XK1kHCgJUVCAOY7Sc5AcakhD3pWi0m3; galaxy.creator.beaker.session.id=1748055476114025081990; acw_tc=0a0d0eb817480719748146733e74eac8f8db0a3f5aa727beffc942b19d74c0; webBuild=4.62.3; loadts=1748072170704; websectiga=2845367ec3848418062e761c09db7caf0e8b79d132ccdd1a4f8e64a11d0cac0d; sec_poison_id=4a2e00d6-6a8a-42eb-bcec-9253ab86953a; xsecappid=creator-creator'
    # 获取用户信息
    user_url = 'https://www.xiaohongshu.com/user/profile/67a332a2000000000d008358?xsec_token=ABTf9yz4cLHhTycIlksF0jOi1yIZgfcaQ6IXNNGdKJ8xg=&xsec_source=pc_feed'
    success, msg, user_info = xhs_apis.get_note_data( cookies_str)
    logger.info(f'获取用户信息结果 {json.dumps(user_info, ensure_ascii=False)}: {success}, msg: {msg}')
    # success, msg, note_list = xhs_apis.get_user_all_notes(user_url, cookies_str)
    # logger.info(f'获取用户所有笔记结果 {json.dumps(note_list, ensure_ascii=False)}: {success}, msg: {msg}')
    # # 获取笔记信息
    # note_url = r'https://www.xiaohongshu.com/explore/67d7c713000000000900e391?xsec_token=AB1ACxbo5cevHxV_bWibTmK8R1DDz0NnAW1PbFZLABXtE=&xsec_source=pc_user'
    # success, msg, note_info = xhs_apis.get_note_info(note_url, cookies_str)
    # logger.info(f'获取笔记信息结果 {json.dumps(note_info, ensure_ascii=False)}: {success}, msg: {msg}')
    # # 获取搜索关键词
    # query = "榴莲"
    # success, msg, search_keyword = xhs_apis.get_search_keyword(query, cookies_str)
    # logger.info(f'获取搜索关键词结果 {json.dumps(search_keyword, ensure_ascii=False)}: {success}, msg: {msg}')
    # # 搜索笔记
    # query = "榴莲"
    # query_num = 10
    # sort = "general"
    # note_type = 0
    # success, msg, notes = xhs_apis.search_some_note(query, query_num, cookies_str, sort, note_type)
    # logger.info(f'搜索笔记结果 {json.dumps(notes, ensure_ascii=False)}: {success}, msg: {msg}')
    # # 获取笔记评论
    # note_url = r'https://www.xiaohongshu.com/explore/67d7c713000000000900e391?xsec_token=AB1ACxbo5cevHxV_bWibTmK8R1DDz0NnAW1PbFZLABXtE=&xsec_source=pc_user'
    # success, msg, note_all_comment = xhs_apis.get_note_all_comment(note_url, cookies_str)
    # logger.info(f'获取笔记评论结果 {json.dumps(note_all_comment, ensure_ascii=False)}: {success}, msg: {msg}')