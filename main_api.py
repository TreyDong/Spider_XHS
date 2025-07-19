# encoding: utf-8
from datetime import datetime
from typing import List
import psycopg2
import json

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

from apis.creator import Creator_Apis
from apis.notion import NotionApi
from apis.notion import call_siliconflow_transcription_from_url
from apis.xhs_pc_apis import XHS_Apis
from proxy import read_proxies, get_working_proxy
from apis.blogger_scraper import scrape_blogger_by_id_api

app = FastAPI()
xhs_apis = XHS_Apis()
creator_apis = Creator_Apis()
notion_api = NotionApi()
proxies_list = read_proxies()

class ScrapeBloggerByIdRequest(BaseModel):
    user_id: str

@app.post("/api/scrape_blogger_by_id")
def scrape_blogger_by_id(request: ScrapeBloggerByIdRequest, background_tasks: BackgroundTasks):
    return scrape_blogger_by_id_api(request.user_id, background_tasks=background_tasks)

def _get_db_config():
    import os
    from dotenv import load_dotenv
    load_dotenv()
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'dbname': os.getenv('DB_NAME', 'xhs_spider'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', '')
    }

@app.get("/api/scrape_blogger_status/{task_id}")
def get_scrape_blogger_status(task_id: str):
    db_config = _get_db_config()
    conn = None
    try:
        conn = psycopg2.connect(
            host=db_config.get('host', 'localhost'),
            port=db_config.get('port', 5432),
            dbname=db_config.get('dbname', 'xhs_spider'),
            user=db_config.get('user', 'postgres'),
            password=db_config.get('password', '')
        )
        cursor = conn.cursor()
        cursor.execute("SELECT task_id, user_id, status, start_time, end_time, result_summary, error_details FROM scraper_tasks WHERE task_id = %s", (task_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            task_data = {
                "task_id": result[0],
                "user_id": result[1],
                "status": result[2],
                "start_time": result[3].isoformat() if result[3] else None,
                "end_time": result[4].isoformat() if result[4] else None,
                "result_summary": json.loads(result[5]) if result[5] else None,
                "error_details": result[6]
            }
            return task_data
        else:
            raise HTTPException(status_code=404, detail="Task not found")
    except Exception as e:
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Error querying task status: {str(e)}")

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
    cookies_arr: List[str]
    note_url: str = ""
    remarks: str = ""
    custom_tags: str = ""
    video_transfer: bool = False
    video_transfer_api_key: str = ""
    proxies: dict = None

@app.post("/api/save_to_notion")
def save_to_notion(request: SaveToNotionRequest):
    return handle_api_call(notion_api.save_xiaohongshu_note_to_notion, request.notion_token, request.database_id,request.cookies_arr,request.note_url,request.remarks,
                           request.custom_tags,request.video_transfer,request.video_transfer_api_key,get_working_proxy(proxies_list))

class SiliconFlowTranscriptionRequest(BaseModel):
    media_url: str
    api_key: str
    model_name: str = "FunAudioLLM/SenseVoiceSmall"

@app.post("/api/siliconflow_transcription")
async def siliconflow_transcription(request: SiliconFlowTranscriptionRequest):
    """调用SiliconFlow的语音转录API"""
    try:
        # 使用 await 关键字等待协程执行完成并获取结果
        result = await call_siliconflow_transcription_from_url(
            media_url=request.media_url,
            api_key=request.api_key,
            model_name=request.model_name
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/")
def read_root():
    """根目录测试接口，返回简单问候信息"""
    return {"message": "Welcome to the XHS Spider API! This is a test endpoint."}

# 注册博主采集API


if __name__ == "__main__":
    import uvicorn
    from loguru import logger

    logger.add("file.log", level="DEBUG", rotation="10 MB")
    logger.debug("Loguru is configured to DEBUG level.")

    uvicorn.run(app, host="0.0.0.0", port=8000)