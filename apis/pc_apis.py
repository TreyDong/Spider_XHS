# encoding: utf-8
import json
import re
import urllib
import requests
from xhs_utils.xhs_util import splice_str, generate_request_params, generate_x_b3_traceid, get_common_headers
from loguru import logger

"""
    获小红书的api
    :param cookies_str: 你的cookies
"""


def extract_url(text):
    # 正则表达式匹配小红书短链
    pattern = r'http://xhslink\.com/\S+'
    match = re.search(pattern, text)
    if match:
        return match.group(0)  # 返回匹配到的链接
    else:
        return "未找到链接"


def get_redirect_url(short_url):
    try:
        # 添加请求头，模拟浏览器请求
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
        # 发送请求，禁止自动重定向
        response = requests.get(short_url, headers=headers, allow_redirects=False)
        # 检查响应状态码
        if response.status_code in [301, 302, 307]:  # 处理重定向状态码
            redirect_url = response.headers['Location']  # 获取重定向链接
            return redirect_url
        else:
            return "无法获取重定向链接，状态码: {}".format(response.status_code)
    except Exception as e:
        return "请求失败: {}".format(str(e))


class XHS_Apis():
    def __init__(self):
        self.base_url = "https://edith.xiaohongshu.com"

    def get_homefeed_all_channel(self, cookies_str: str, proxies: dict = None):
        """
            获取主页的所有频道
            返回主页的所有频道
        """
        res_json = None
        try:
            api = "/api/sns/web/v1/homefeed/category"
            headers, cookies, data = generate_request_params(cookies_str, api)
            response = requests.get(self.base_url + api, headers=headers, cookies=cookies, proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_homefeed_recommend(self, category, cursor_score, refresh_type, note_index, cookies_str: str,
                               proxies: dict = None):
        """
            获取主页推荐的笔记
            :param category: 你想要获取的频道
            :param cursor_score: 你想要获取的笔记的cursor
            :param refresh_type: 你想要获取的笔记的刷新类型
            :param note_index: 你想要获取的笔记的index
            :param cookies_str: 你的cookies
            返回主页推荐的笔记
        """
        res_json = None
        try:
            api = f"/api/sns/web/v1/homefeed"
            data = {
                "cursor_score": cursor_score,
                "num": 20,
                "refresh_type": refresh_type,
                "note_index": note_index,
                "unread_begin_note_id": "",
                "unread_end_note_id": "",
                "unread_note_count": 0,
                "category": category,
                "search_key": "",
                "need_num": 10,
                "image_formats": [
                    "jpg",
                    "webp",
                    "avif"
                ],
                "need_filter_image": False
            }
            headers, cookies, trans_data = generate_request_params(cookies_str, api, data)
            response = requests.post(self.base_url + api, headers=headers, data=trans_data, cookies=cookies,
                                     proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_homefeed_recommend_by_num(self, category, require_num, cookies_str: str, proxies: dict = None):
        """
            根据数量获取主页推荐的笔记
            :param category: 你想要获取的频道
            :param require_num: 你想要获取的笔记的数量
            :param cookies_str: 你的cookies
            根据数量返回主页推荐的笔记
        """
        cursor_score, refresh_type, note_index = "", 1, 0
        note_list = []
        try:
            while True:
                success, msg, res_json = self.get_homefeed_recommend(category, cursor_score, refresh_type, note_index,
                                                                     cookies_str, proxies)
                if not success:
                    raise Exception(msg)
                if "items" not in res_json["data"]:
                    break
                notes = res_json["data"]["items"]
                note_list.extend(notes)
                cursor_score = res_json["data"]["cursor_score"]
                refresh_type = 3
                note_index += 20
                if len(note_list) > require_num:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        if len(note_list) > require_num:
            note_list = note_list[:require_num]
        return success, msg, note_list

    def get_user_info(self, user_id: str, cookies_str: str, proxies: dict = None):
        """
            获取用户的信息
            :param user_id: 你想要获取的用户的id
            :param cookies_str: 你的cookies
            返回用户的信息
        """
        res_json = None
        try:
            api = f"/api/sns/web/v1/user/otherinfo"
            params = {
                "target_user_id": user_id
            }
            splice_api = splice_str(api, params)
            headers, cookies, data = generate_request_params(cookies_str, splice_api)
            response = requests.get(self.base_url + splice_api, headers=headers, cookies=cookies, proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_user_self_info(self, cookies_str: str, proxies: dict = None):
        """
            获取用户自己的信息1
            :param cookies_str: 你的cookies
            返回用户自己的信息1
        """
        res_json = None
        try:
            api = f"/api/sns/web/v1/user/selfinfo"
            headers, cookies, data = generate_request_params(cookies_str, api)
            response = requests.get(self.base_url + api, headers=headers, cookies=cookies, proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_user_self_info2(self, cookies_str: str, proxies: dict = None):
        """
            获取用户自己的信息2
            :param cookies_str: 你的cookies
            返回用户自己的信息2
        """
        res_json = None
        try:
            api = f"/api/sns/web/v2/user/me"
            headers, cookies, data = generate_request_params(cookies_str, api)
            response = requests.get(self.base_url + api, headers=headers, cookies=cookies, proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_user_note_info(self, user_id: str, cursor: str, cookies_str: str, xsec_token='', xsec_source='',
                           proxies: dict = None):
        """
            获取用户指定位置的笔记
            :param user_id: 你想要获取的用户的id
            :param cursor: 你想要获取的笔记的cursor
            :param cookies_str: 你的cookies
            返回用户指定位置的笔记
        """
        res_json = None
        try:
            api = f"/api/sns/web/v1/user_posted"
            params = {
                "num": "30",
                "cursor": cursor,
                "user_id": user_id,
                "image_formats": "jpg,webp,avif",
                "xsec_token": xsec_token,
                "xsec_source": xsec_source,
            }
            splice_api = splice_str(api, params)
            headers, cookies, data = generate_request_params(cookies_str, splice_api)
            response = requests.get(self.base_url + splice_api, headers=headers, cookies=cookies, proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_user_all_notes(self, user_url: str, cookies_str: str, proxies: dict = None):
        """
           获取用户所有笔记
           :param user_url:
           :param user_id: 你想要获取的用户的id
           :param cookies_str: 你的cookies
           返回用户的所有笔记
        """
        cursor = ''
        note_list = []
        try:
            urlParse = urllib.parse.urlparse(user_url)
            user_id = urlParse.path.split("/")[-1]
            kvs = urlParse.query.split('&')
            kvDist = {kv.split('=')[0]: kv.split('=')[1] for kv in kvs}
            xsec_token = kvDist['xsec_token'] if 'xsec_token' in kvDist else ""
            xsec_source = kvDist['xsec_source'] if 'xsec_source' in kvDist else "pc_search"
            while True:
                success, msg, res_json = self.get_user_note_info(user_id, cursor, cookies_str, xsec_token, xsec_source,
                                                                 proxies)
                if not success:
                    raise Exception(msg)
                notes = res_json["data"]["notes"]
                if 'cursor' in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                note_list.extend(notes)
                if len(notes) == 0 or not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, note_list

    def get_user_like_note_info(self, user_id: str, cursor: str, cookies_str: str, xsec_token='', xsec_source='',
                                proxies: dict = None):
        """
            获取用户指定位置喜欢的笔记
            :param user_id: 你想要获取的用户的id
            :param cursor: 你想要获取的笔记的cursor
            :param cookies_str: 你的cookies
            返回用户指定位置喜欢的笔记
        """
        res_json = None
        try:
            api = f"/api/sns/web/v1/note/like/page"
            params = {
                "num": "30",
                "cursor": cursor,
                "user_id": user_id,
                "image_formats": "jpg,webp,avif",
                "xsec_token": xsec_token,
                "xsec_source": xsec_source,
            }
            splice_api = splice_str(api, params)
            headers, cookies, data = generate_request_params(cookies_str, splice_api)
            response = requests.get(self.base_url + splice_api, headers=headers, cookies=cookies, proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_user_all_like_note_info(self, user_url: str, cookies_str: str, proxies: dict = None):
        """
            获取用户所有喜欢笔记
            :param user_id: 你想要获取的用户的id
            :param cookies_str: 你的cookies
            返回用户的所有喜欢笔记
        """
        cursor = ''
        note_list = []
        try:
            urlParse = urllib.parse.urlparse(user_url)
            user_id = urlParse.path.split("/")[-1]
            kvs = urlParse.query.split('&')
            kvDist = {kv.split('=')[0]: kv.split('=')[1] for kv in kvs}
            xsec_token = kvDist['xsec_token'] if 'xsec_token' in kvDist else ""
            xsec_source = kvDist['xsec_source'] if 'xsec_source' in kvDist else "pc_user"
            while True:
                success, msg, res_json = self.get_user_like_note_info(user_id, cursor, cookies_str, xsec_token,
                                                                      xsec_source, proxies)
                if not success:
                    raise Exception(msg)
                notes = res_json["data"]["notes"]
                if 'cursor' in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                note_list.extend(notes)
                if len(notes) == 0 or not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, note_list

    def get_user_collect_note_info(self, user_id: str, cursor: str, cookies_str: str, xsec_token='', xsec_source='',
                                   proxies: dict = None):
        """
            获取用户指定位置收藏的笔记
            :param user_id: 你想要获取的用户的id
            :param cursor: 你想要获取的笔记的cursor
            :param cookies_str: 你的cookies
            返回用户指定位置收藏的笔记
        """
        res_json = None
        try:
            api = f"/api/sns/web/v2/note/collect/page"
            params = {
                "num": "30",
                "cursor": cursor,
                "user_id": user_id,
                "image_formats": "jpg,webp,avif",
                "xsec_token": xsec_token,
                "xsec_source": xsec_source,
            }
            splice_api = splice_str(api, params)
            headers, cookies, data = generate_request_params(cookies_str, splice_api)
            response = requests.get(self.base_url + splice_api, headers=headers, cookies=cookies, proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_user_all_collect_note_info(self, user_url: str, cookies_str: str, proxies: dict = None):
        """
            获取用户所有收藏笔记
            :param user_id: 你想要获取的用户的id
            :param cookies_str: 你的cookies
            返回用户的所有收藏笔记
        """
        cursor = ''
        note_list = []
        try:
            urlParse = urllib.parse.urlparse(user_url)
            user_id = urlParse.path.split("/")[-1]
            kvs = urlParse.query.split('&')
            kvDist = {kv.split('=')[0]: kv.split('=')[1] for kv in kvs}
            xsec_token = kvDist['xsec_token'] if 'xsec_token' in kvDist else ""
            xsec_source = kvDist['xsec_source'] if 'xsec_source' in kvDist else "pc_search"
            while True:
                success, msg, res_json = self.get_user_collect_note_info(user_id, cursor, cookies_str, xsec_token,
                                                                         xsec_source, proxies)
                if not success:
                    raise Exception(msg)
                notes = res_json["data"]["notes"]
                if 'cursor' in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                note_list.extend(notes)
                if len(notes) == 0 or not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, note_list

    def get_note_info(self, url: str, cookies_str: str, proxies: dict = None):
        """
            获取笔记的详细
            :param proxies:
            :param url: 你想要获取的笔记的url
            :param cookies_str: 你的cookies
            返回笔记的详细
        """

        res_json = None
        try:
            if "笔记" in url:
                url = extract_url(url)
                url = get_redirect_url(url)
            urlParse = urllib.parse.urlparse(url)
            note_id = urlParse.path.split("/")[-1]
            kvs = urlParse.query.split('&')
            kvDist = {kv.split('=')[0]: kv.split('=')[1] for kv in kvs}
            api = f"/api/sns/web/v1/feed"
            data = {
                "source_note_id": note_id,
                "image_formats": [
                    "jpg",
                    "webp",
                    "avif"
                ],
                "extra": {
                    "need_body_topic": "1"
                },
                "xsec_source": kvDist['xsec_source'] if 'xsec_source' in kvDist else "pc_search",
                "xsec_token": kvDist['xsec_token']
            }
            headers, cookies, data = generate_request_params(cookies_str, api, data)
            response = requests.post(self.base_url + api, headers=headers, data=data, cookies=cookies, proxies=proxies)
            if response.status_code == 200:
                res_json = response.json()
                success, msg = res_json["success"], res_json["msg"]
            else:
                success = False
                msg = "请求失败，状态码: {}".format(response.status_code)
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_search_keyword(self, word: str, cookies_str: str, proxies: dict = None):
        """
            获取搜索关键词
            :param word: 你的关键词
            :param cookies_str: 你的cookies
            返回搜索关键词
        """
        res_json = None
        try:
            api = "/api/sns/web/v1/search/recommend"
            params = {
                "keyword": urllib.parse.quote(word)
            }
            splice_api = splice_str(api, params)
            headers, cookies, data = generate_request_params(cookies_str, splice_api)
            response = requests.get(self.base_url + splice_api, headers=headers, cookies=cookies, proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def search_note(self, query: str, cookies_str: str, page=1, sort="general", note_type=0, proxies: dict = None):
        """
            获取搜索笔记的结果
            :param query 搜索的关键词
            :param cookies_str 你的cookies
            :param page 搜索的页数
            :param sort 排序方式 general:综合排序, time_descending:时间排序, popularity_descending:热度排序
            :param note_type 笔记类型 0:全部, 1:视频, 2:图文
            返回搜索的结果
        """
        res_json = None
        try:
            api = "/api/sns/web/v1/search/notes"
            data = {
                "keyword": query,
                "page": page,
                "page_size": 20,
                "search_id": generate_x_b3_traceid(21),
                "sort": sort,
                "note_type": note_type,
                "ext_flags": [],
                "image_formats": [
                    "jpg",
                    "webp",
                    "avif"
                ]
            }
            headers, cookies, data = generate_request_params(cookies_str, api, data)
            response = requests.post(self.base_url + api, headers=headers, data=data.encode('utf-8'), cookies=cookies,
                                     proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def search_some_note(self, query: str, require_num: int, cookies_str: str, sort="general", note_type=0,
                         proxies: dict = None):
        """
            指定数量搜索笔记，设置排序方式和笔记类型和笔记数量
            :param query 搜索的关键词
            :param require_num 搜索的数量
            :param cookies_str 你的cookies
            :param sort 排序方式 general:综合排序, time_descending:时间排序, popularity_descending:热度排序
            :param note_type 笔记类型 0:全部, 1:视频, 2:图文
            返回搜索的结果
        """
        page = 1
        note_list = []
        try:
            while True:
                success, msg, res_json = self.search_note(query, cookies_str, page, sort, note_type, proxies)
                if not success:
                    raise Exception(msg)
                if "items" not in res_json["data"]:
                    break
                notes = res_json["data"]["items"]
                note_list.extend(notes)
                page += 1
                if len(note_list) >= require_num or not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        if len(note_list) > require_num:
            note_list = note_list[:require_num]
        return success, msg, note_list

    def search_user(self, query: str, cookies_str: str, page=1, proxies: dict = None):
        """
            获取搜索用户的结果
            :param query 搜索的关键词
            :param cookies_str 你的cookies
            :param page 搜索的页数
            返回搜索的结果
        """
        res_json = None
        try:
            api = "/api/sns/web/v1/search/usersearch"
            data = {
                "search_user_request": {
                    "keyword": query,
                    "search_id": "2dn9they1jbjxwawlo4xd",
                    "page": page,
                    "page_size": 15,
                    "biz_type": "web_search_user",
                    "request_id": "22471139-1723999898524"
                }
            }
            headers, cookies, data = generate_request_params(cookies_str, api, data)
            response = requests.post(self.base_url + api, headers=headers, data=data.encode('utf-8'), cookies=cookies,
                                     proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def search_some_user(self, query: str, require_num: int, cookies_str: str, proxies: dict = None):
        """
            指定数量搜索用户
            :param query 搜索的关键词
            :param require_num 搜索的数量
            :param cookies_str 你的cookies
            返回搜索的结果
        """
        page = 1
        user_list = []
        try:
            while True:
                success, msg, res_json = self.search_user(query, cookies_str, page, proxies)
                if not success:
                    raise Exception(msg)
                if "users" not in res_json["data"]:
                    break
                users = res_json["data"]["users"]
                user_list.extend(users)
                page += 1
                if len(user_list) >= require_num or not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        if len(user_list) > require_num:
            user_list = user_list[:require_num]
        return success, msg, user_list

    def get_note_out_comment(self, note_id: str, cursor: str, xsec_token: str, cookies_str: str, proxies: dict = None):
        """
            获取指定位置的笔记一级评论
            :param note_id 笔记的id
            :param cursor 指定位置的评论的cursor
            :param cookies_str 你的cookies
            返回指定位置的笔记一级评论
        """
        res_json = None
        try:
            api = "/api/sns/web/v2/comment/page"
            params = {
                "note_id": note_id,
                "cursor": cursor,
                "top_comment_id": "",
                "image_formats": "jpg,webp,avif",
                "xsec_token": xsec_token
            }
            splice_api = splice_str(api, params)
            headers, cookies, data = generate_request_params(cookies_str, splice_api)
            response = requests.get(self.base_url + splice_api, headers=headers, cookies=cookies, proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_note_all_out_comment(self, note_id: str, xsec_token: str, cookies_str: str, proxies: dict = None):
        """
            获取笔记的全部一级评论
            :param note_id 笔记的id
            :param cookies_str 你的cookies
            返回笔记的全部一级评论
        """
        cursor = ''
        note_out_comment_list = []
        try:
            while True:
                success, msg, res_json = self.get_note_out_comment(note_id, cursor, xsec_token, cookies_str, proxies)
                if not success:
                    raise Exception(msg)
                comments = res_json["data"]["comments"]
                if 'cursor' in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                note_out_comment_list.extend(comments)
                if len(note_out_comment_list) == 0 or not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, note_out_comment_list

    def get_note_inner_comment(self, comment: dict, cursor: str, xsec_token: str, cookies_str: str,
                               proxies: dict = None):
        """
            获取指定位置的笔记二级评论
            :param comment 笔记的一级评论
            :param cursor 指定位置的评论的cursor
            :param cookies_str 你的cookies
            返回指定位置的笔记二级评论
        """
        res_json = None
        try:
            api = "/api/sns/web/v2/comment/sub/page"
            params = {
                "note_id": comment['note_id'],
                "root_comment_id": comment['id'],
                "num": "10",
                "cursor": cursor,
                "image_formats": "jpg,webp,avif",
                "top_comment_id": '',
                "xsec_token": xsec_token
            }
            splice_api = splice_str(api, params)
            headers, cookies, data = generate_request_params(cookies_str, splice_api)
            response = requests.get(self.base_url + splice_api, headers=headers, cookies=cookies, proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_note_all_inner_comment(self, comment: dict, xsec_token: str, cookies_str: str, proxies: dict = None):
        """
            获取笔记的全部二级评论
            :param comment 笔记的一级评论
            :param cookies_str 你的cookies
            返回笔记的全部二级评论
        """
        try:
            if not comment['sub_comment_has_more']:
                return True, 'success', comment
            cursor = comment['sub_comment_cursor']
            inner_comment_list = []
            while True:
                success, msg, res_json = self.get_note_inner_comment(comment, cursor, xsec_token, cookies_str, proxies)
                if not success:
                    raise Exception(msg)
                comments = res_json["data"]["comments"]
                if 'cursor' in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                inner_comment_list.extend(comments)
                if not res_json["data"]["has_more"]:
                    break
            comment['sub_comments'].extend(inner_comment_list)
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, comment

    def get_note_all_comment(self, url: str, cookies_str: str, proxies: dict = None):
        """
            获取一篇文章的所有评论
            :param note_id: 你想要获取的笔记的id
            :param cookies_str: 你的cookies
            返回一篇文章的所有评论
        """
        out_comment_list = []
        try:
            urlParse = urllib.parse.urlparse(url)
            note_id = urlParse.path.split("/")[-1]
            kvs = urlParse.query.split('&')
            kvDist = {kv.split('=')[0]: kv.split('=')[1] for kv in kvs}
            success, msg, out_comment_list = self.get_note_all_out_comment(note_id, kvDist['xsec_token'], cookies_str,
                                                                           proxies)
            if not success:
                raise Exception(msg)
            for comment in out_comment_list:
                success, msg, new_comment = self.get_note_all_inner_comment(comment, kvDist['xsec_token'], cookies_str,
                                                                            proxies)
                if not success:
                    raise Exception(msg)
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, out_comment_list

    def get_unread_message(self, cookies_str: str, proxies: dict = None):
        """
            获取未读消息
            :param cookies_str: 你的cookies
            返回未读消息
        """
        res_json = None
        try:
            api = "/api/sns/web/unread_count"
            headers, cookies, data = generate_request_params(cookies_str, api)
            response = requests.get(self.base_url + api, headers=headers, cookies=cookies, proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_metions(self, cursor: str, cookies_str: str, proxies: dict = None):
        """
            获取评论和@提醒
            :param cursor: 你想要获取的评论和@提醒的cursor
            :param cookies_str: 你的cookies
            返回评论和@提醒
        """
        res_json = None
        try:
            api = "/api/sns/web/v1/you/mentions"
            params = {
                "num": "20",
                "cursor": cursor
            }
            splice_api = splice_str(api, params)
            headers, cookies, data = generate_request_params(cookies_str, splice_api)
            response = requests.get(self.base_url + splice_api, headers=headers, cookies=cookies, proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_all_metions(self, cookies_str: str, proxies: dict = None):
        """
            获取全部的评论和@提醒
            :param cookies_str: 你的cookies
            返回全部的评论和@提醒
        """
        cursor = ''
        metions_list = []
        try:
            while True:
                success, msg, res_json = self.get_metions(cursor, cookies_str, proxies)
                if not success:
                    raise Exception(msg)
                metions = res_json["data"]["message_list"]
                if 'cursor' in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                metions_list.extend(metions)
                if not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, metions_list

    def get_likesAndcollects(self, cursor: str, cookies_str: str, proxies: dict = None):
        """
            获取赞和收藏
            :param cursor: 你想要获取的赞和收藏的cursor
            :param cookies_str: 你的cookies
            返回赞和收藏
        """
        res_json = None
        try:
            api = "/api/sns/web/v1/you/likes"
            params = {
                "num": "20",
                "cursor": cursor
            }
            splice_api = splice_str(api, params)
            headers, cookies, data = generate_request_params(cookies_str, splice_api)
            response = requests.get(self.base_url + splice_api, headers=headers, cookies=cookies, proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_all_likesAndcollects(self, cookies_str: str, proxies: dict = None):
        """
            获取全部的赞和收藏
            :param cookies_str: 你的cookies
            返回全部的赞和收藏
        """
        cursor = ''
        likesAndcollects_list = []
        try:
            while True:
                success, msg, res_json = self.get_likesAndcollects(cursor, cookies_str, proxies)
                if not success:
                    raise Exception(msg)
                likesAndcollects = res_json["data"]["message_list"]
                if 'cursor' in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                likesAndcollects_list.extend(likesAndcollects)
                if not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, likesAndcollects_list

    def get_new_connections(self, cursor: str, cookies_str: str, proxies: dict = None):
        """
            获取新增关注
            :param cursor: 你想要获取的新增关注的cursor
            :param cookies_str: 你的cookies
            返回新增关注
        """
        res_json = None
        try:
            api = "/api/sns/web/v1/you/connections"
            params = {
                "num": "20",
                "cursor": cursor
            }
            splice_api = splice_str(api, params)
            headers, cookies, data = generate_request_params(cookies_str, splice_api)
            response = requests.get(self.base_url + splice_api, headers=headers, cookies=cookies, proxies=proxies)
            res_json = response.json()
            success, msg = res_json["success"], res_json["msg"]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, res_json

    def get_all_new_connections(self, cookies_str: str, proxies: dict = None):
        """
            获取全部的新增关注
            :param cookies_str: 你的cookies
            返回全部的新增关注
        """
        cursor = ''
        connections_list = []
        try:
            while True:
                success, msg, res_json = self.get_new_connections(cursor, cookies_str, proxies)
                if not success:
                    raise Exception(msg)
                connections = res_json["data"]["message_list"]
                if 'cursor' in res_json["data"]:
                    cursor = str(res_json["data"]["cursor"])
                else:
                    break
                connections_list.extend(connections)
                if not res_json["data"]["has_more"]:
                    break
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, connections_list

    @staticmethod
    def get_note_no_water_video(note_id):
        """
            获取笔记无水印视频
            :param note_id: 你想要获取的笔记的id
            返回笔记无水印视频
        """
        success = True
        msg = '成功'
        video_addr = None
        try:
            headers = get_common_headers()
            url = f"https://www.xiaohongshu.com/explore/{note_id}"
            response = requests.get(url, headers=headers)
            res = response.text
            video_addr = re.findall(r'<meta name="og:video" content="(.*?)">', res)[0]
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, video_addr

    @staticmethod
    def get_note_no_water_img(img_url):
        """
            获取笔记无水印图片
            :param img_url: 你想要获取的图片的url
            返回笔记无水印图片
        """
        success = True
        msg = '成功'
        new_url = None
        try:
            # https://sns-webpic-qc.xhscdn.com/202403211626/c4fcecea4bd012a1fe8d2f1968d6aa91/110/0/01e50c1c135e8c010010000000018ab74db332_0.jpg!nd_dft_wlteh_webp_3
            if '.jpg' in img_url:
                img_id = '/'.join([split for split in img_url.split('/')[-3:]]).split('!')[0]
                # return f"http://ci.xiaohongshu.com/{img_id}?imageview2/2/w/1920/format/png"
                # return f"http://ci.xiaohongshu.com/{img_id}?imageview2/2/w/format/png"
                # return f'https://sns-img-hw.xhscdn.com/{img_id}'
                new_url = f'https://sns-img-qc.xhscdn.com/{img_id}'

            # 'https://sns-webpic-qc.xhscdn.com/202403231640/ea961053c4e0e467df1cc93afdabd630/spectrum/1000g0k0200n7mj8fq0005n7ikbllol6q50oniuo!nd_dft_wgth_webp_3'
            elif 'spectrum' in img_url:
                img_id = '/'.join(img_url.split('/')[-2:]).split('!')[0]
                # return f'http://sns-webpic.xhscdn.com/{img_id}?imageView2/2/w/1920/format/jpg'
                new_url = f'http://sns-webpic.xhscdn.com/{img_id}?imageView2/2/w/format/jpg'
            else:
                # 'http://sns-webpic-qc.xhscdn.com/202403181511/64ad2ea67ce04159170c686a941354f5/1040g008310cs1hii6g6g5ngacg208q5rlf1gld8!nd_dft_wlteh_webp_3'
                img_id = img_url.split('/')[-1].split('!')[0]
                # return f"http://ci.xiaohongshu.com/{img_id}?imageview2/2/w/1920/format/png"
                # return f"http://ci.xiaohongshu.com/{img_id}?imageview2/2/w/format/png"
                # return f'https://sns-img-hw.xhscdn.com/{img_id}'
                new_url = f'https://sns-img-qc.xhscdn.com/{img_id}'
        except Exception as e:
            success = False
            msg = str(e)
        return success, msg, new_url


if __name__ == '__main__':
    """
        此文件为小红书api的使用示例
        所有涉及数据爬取的api都在此文件中
        数据注入的api违规请勿尝试
    """
    short_url = extract_url(
        "68 大张认知思维发布了一篇小红书笔记，快来看吧！ 😆 1VXOjFFtNOPKkHu 😆 http://xhslink.com/a/Dq3vIEui0creb，复制本条信息，打开【小红书】App查看精彩内容！")
    full_url = get_redirect_url(short_url)
    print(full_url)
    # xhs_apis = XHS_Apis()
    # cookies_str = r'abRequestId=22973d72-15cb-5702-80c8-a471293467c8; a1=19445ba38d63xf7quk41drjq42ccjgh6iqv0oxfds50000303805; webId=f6b4d664989c30e435f9ee109844c381; gid=yj442D04Y03Syj442D0qYACifKqCiWA7T4yfhfMFVA4JS828SVkxKl888q8qY828W0dqyd8W; customerClientId=952214275927397; x-user-id-creator.xiaohongshu.com=623e80890000000010005fd8; xsecappid=xhs-pc-web; webBuild=4.62.3; web_session=0400697766d1cc99bff61731193a4bf2fd2ef3; websectiga=984412fef754c018e472127b8effd174be8a5d51061c991aadd200c69a2801d6; sec_poison_id=68a68ba6-c204-494f-a3e2-63f476f8c593; loadts=1747879378227; unread={%22ub%22:%22682dd5eb0000000012007c53%22%2C%22ue%22:%22682bf0a2000000002300209d%22%2C%22uc%22:30}'
    # # 获取用户信息
    # user_url = 'https://www.xiaohongshu.com/user/profile/6807735a000000000a03e8d0'
    # success, msg, user_info = xhs_apis.get_user_info('6807735a000000000a03e8d0', cookies_str)
    # logger.info(f'获取用户信息结果 {json.dumps(user_info, ensure_ascii=False)}: {success}, msg: {msg}')
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
