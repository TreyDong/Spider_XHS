# encoding: utf-8
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from apis.creator import Creator_Apis
from apis.notion import NotionApi
from apis.pc_apis import XHS_Apis
from proxy import read_proxies, get_working_proxy

app = FastAPI()
xhs_apis = XHS_Apis()
creator_apis = Creator_Apis()
notion_api = NotionApi()
proxies_list = read_proxies()


def handle_api_call(func, *args, **kwargs):
    try:
        success, msg, res = func(*args, **kwargs)
        if success:
            return res
        else:
            raise HTTPException(status_code=500, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# pc_apis.py 相关接口
class GetHomefeedAllChannelRequest(BaseModel):
    cookies_str: str
    proxies: dict = None

@app.post("/api/get_homefeed_all_channel")
def get_homefeed_all_channel(request: GetHomefeedAllChannelRequest):
    """获取主页的所有频道"""
    return handle_api_call(xhs_apis.get_homefeed_all_channel, request.cookies_str,get_working_proxy(proxies_list))

class GetHomefeedRecommendRequest(BaseModel):
    category: str
    cursor_score: str
    refresh_type: int
    note_index: int
    cookies_str: str
    proxies: dict = None

@app.post("/api/get_homefeed_recommend")
def get_homefeed_recommend(request: GetHomefeedRecommendRequest):
    """获取主页推荐的笔记"""
    return handle_api_call(xhs_apis.get_homefeed_recommend, request.category, request.cursor_score, request.refresh_type, request.note_index, request.cookies_str,get_working_proxy(proxies_list))

class GetHomefeedRecommendByNumRequest(BaseModel):
    category: str
    require_num: int
    cookies_str: str
    proxies: dict = None

@app.post("/api/get_homefeed_recommend_by_num")
def get_homefeed_recommend_by_num(request: GetHomefeedRecommendByNumRequest):
    """根据数量获取主页推荐的笔记"""
    return handle_api_call(xhs_apis.get_homefeed_recommend_by_num, request.category, request.require_num, request.cookies_str,get_working_proxy(proxies_list))

class GetUserInfoRequest(BaseModel):
    user_id: str
    cookies_str: str
    proxies: dict = None

@app.post("/api/get_user_info")
def get_user_info(request: GetUserInfoRequest):
    """获取用户的信息"""
    return handle_api_call(xhs_apis.get_user_info, request.user_id, request.cookies_str,get_working_proxy(proxies_list))

class GetUserSelfInfoRequest(BaseModel):
    cookies_str: str
    proxies: dict = None

@app.post("/api/get_user_self_info")
def get_user_self_info(request: GetUserSelfInfoRequest):
    """获取用户自己的信息1"""
    return handle_api_call(xhs_apis.get_user_self_info, request.cookies_str,get_working_proxy(proxies_list))

@app.post("/api/get_user_self_info2")
def get_user_self_info2(request: GetUserSelfInfoRequest):
    """获取用户自己的信息2"""
    return handle_api_call(xhs_apis.get_user_self_info2, request.cookies_str,get_working_proxy(proxies_list))

class GetUserNoteInfoRequest(BaseModel):
    user_id: str
    cursor: str
    cookies_str: str
    xsec_token: str = ''
    xsec_source: str = ''
    proxies: dict = None

@app.post("/api/get_user_note_info")
def get_user_note_info(request: GetUserNoteInfoRequest):
    """获取用户指定位置的笔记"""
    return handle_api_call(xhs_apis.get_user_note_info, request.user_id, request.cursor, request.cookies_str, request.xsec_token, request.xsec_source,get_working_proxy(proxies_list))

class GetUserAllNotesRequest(BaseModel):
    user_url: str
    cookies_str: str
    proxies: dict = None

@app.post("/api/get_user_all_notes")
def get_user_all_notes(request: GetUserAllNotesRequest):
    """获取用户所有笔记"""
    return handle_api_call(xhs_apis.get_user_all_notes, request.user_url, request.cookies_str,get_working_proxy(proxies_list))

class GetUserLikeNoteInfoRequest(BaseModel):
    user_id: str
    cursor: str
    cookies_str: str
    xsec_token: str = ''
    xsec_source: str = ''
    proxies: dict = None

@app.post("/api/get_user_like_note_info")
def get_user_like_note_info(request: GetUserLikeNoteInfoRequest):
    """获取用户指定位置喜欢的笔记"""
    return handle_api_call(xhs_apis.get_user_like_note_info, request.user_id, request.cursor, request.cookies_str, request.xsec_token, request.xsec_source,get_working_proxy(proxies_list))

class GetUserAllLikeNoteInfoRequest(BaseModel):
    user_url: str
    cookies_str: str
    proxies: dict = None

@app.post("/api/get_user_all_like_note_info")
def get_user_all_like_note_info(request: GetUserAllLikeNoteInfoRequest):
    """获取用户所有喜欢笔记"""
    return handle_api_call(xhs_apis.get_user_all_like_note_info, request.user_url, request.cookies_str,get_working_proxy(proxies_list))

class GetUserCollectNoteInfoRequest(BaseModel):
    user_id: str
    cursor: str
    cookies_str: str
    xsec_token: str = ''
    xsec_source: str = ''
    proxies: dict = None

@app.post("/api/get_user_collect_note_info")
def get_user_collect_note_info(request: GetUserCollectNoteInfoRequest):
    """获取用户指定位置收藏的笔记"""
    return handle_api_call(xhs_apis.get_user_collect_note_info, request.user_id, request.cursor, request.cookies_str, request.xsec_token, request.xsec_source,get_working_proxy(proxies_list))

class GetUserAllCollectNoteInfoRequest(BaseModel):
    user_url: str
    cookies_str: str
    proxies: dict = None

@app.post("/api/get_user_all_collect_note_info")
def get_user_all_collect_note_info(request: GetUserAllCollectNoteInfoRequest):
    """获取用户所有收藏笔记"""
    return handle_api_call(xhs_apis.get_user_all_collect_note_info, request.user_url, request.cookies_str,get_working_proxy(proxies_list))

class GetNoteInfoRequest(BaseModel):
    url: str
    cookies_str: str
    proxies: dict = None

@app.post("/api/get_note_info")
def get_note_info(request: GetNoteInfoRequest):
    """获取笔记的详细"""
    return handle_api_call(xhs_apis.get_note_info, request.url, request.cookies_str,get_working_proxy(proxies_list))

class GetSearchKeywordRequest(BaseModel):
    word: str
    cookies_str: str
    proxies: dict = None

@app.post("/api/get_search_keyword")
def get_search_keyword(request: GetSearchKeywordRequest):
    """获取搜索关键词"""
    return handle_api_call(xhs_apis.get_search_keyword, request.word, request.cookies_str,get_working_proxy(proxies_list))

class SearchNoteRequest(BaseModel):
    query: str
    cookies_str: str
    page: int = 1
    sort: str = "general"
    note_type: int = 0
    proxies: dict = None

@app.post("/api/search_note")
def search_note(request: SearchNoteRequest):
    """获取搜索笔记的结果"""
    return handle_api_call(xhs_apis.search_note, request.query, request.cookies_str, request.page, request.sort, request.note_type,get_working_proxy(proxies_list))

class SearchSomeNoteRequest(BaseModel):
    query: str
    require_num: int
    cookies_str: str
    sort: str = "general"
    note_type: int = 0
    proxies: dict = None

@app.post("/api/search_some_note")
def search_some_note(request: SearchSomeNoteRequest):
    """指定数量搜索笔记，设置排序方式和笔记类型和笔记数量"""
    return handle_api_call(xhs_apis.search_some_note, request.query, request.require_num, request.cookies_str, request.sort, request.note_type,get_working_proxy(proxies_list))

class SearchUserRequest(BaseModel):
    query: str
    cookies_str: str
    page: int = 1
    proxies: dict = None

@app.post("/api/search_user")
def search_user(request: SearchUserRequest):
    """获取搜索用户的结果"""
    return handle_api_call(xhs_apis.search_user, request.query, request.cookies_str, request.page,get_working_proxy(proxies_list))

# creator.py 相关接口
class GetNoteDataRequest(BaseModel):
    cookies_str: str
    post_begin_date: str = None
    post_end_date: str = None
    type: int = 0
    page_size: int = 10
    page_num: int = 1

@app.post("/api/get_note_data")
def get_note_data(request: GetNoteDataRequest):
    """获取笔记数据"""
    if request.post_begin_date:
        request.post_begin_date = datetime.strptime(request.post_begin_date, '%Y-%m-%d')
    if request.post_end_date:
        request.post_end_date = datetime.strptime(request.post_end_date, '%Y-%m-%d')
    return handle_api_call(creator_apis.get_note_data, request.cookies_str, request.post_begin_date, request.post_end_date, request.type, request.page_size, request.page_num)

class NoteDataDetailRequest(BaseModel):
    cookies_str: str
    note_id: str

@app.post("/api/get_note_data_detail")
def get_note_data_detail(request: NoteDataDetailRequest):
    return handle_api_call(creator_apis.get_note_data_detail, request.cookies_str, request.note_id)


@app.post("/api/get_note_data_detail")
def get_note_data_detail(request: NoteDataDetailRequest):
    return handle_api_call(creator_apis.get_note_data_detail, request.cookies_str, request.note_id)

class SaveToNotionRequest(BaseModel):
    notion_token: str
    database_id: str
    cookies_str: str
    note_url: str = ""
    remarks: str = ""
    custom_tags: str = ""
    proxies: dict = None

@app.post("/api/save_to_notion")
def save_to_notion(request: SaveToNotionRequest):
    return handle_api_call(notion_api.save_xiaohongshu_note_to_notion, request.notion_token, request.database_id,request.cookies_str,request.note_url,request.remarks,request.custom_tags,get_working_proxy(proxies_list))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)