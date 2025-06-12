import concurrent.futures
import json
import time
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from urllib.parse import urlparse, urlunparse
import requests
from notion_client import Client
from notion_client.errors import APIResponseError

from apis.pc_apis import XHS_Apis, extract_url, get_redirect_url



def _make_request_with_retry(
        method: str,
        url: str,
        headers: dict,
        max_retries: int = 3,
        **kwargs
) -> requests.Response:
    """
    发送一个HTTP请求，并在遇到429速率限制错误时自动重试。

    :param method: HTTP方法 (e.g., 'get', 'post').
    :param url: 请求的URL.
    :param headers: 请求头.
    :param max_retries: 最大重试次数.
    :param kwargs: 其他传递给 `requests.request` 的参数.
    :return: requests的Response对象.
    :raises: 如果重试后仍然失败，则抛出最后的异常.
    """
    for attempt in range(max_retries):
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()  # 如果是4xx或5xx错误，则抛出HTTPError
            return response
        except requests.exceptions.HTTPError as e:
            # 专门处理429速率限制错误
            if e.response.status_code == 429:
                # 从响应头获取建议的等待时间，默认为1秒
                retry_after = int(e.response.headers.get("Retry-After", 1))
                print(
                    f"⚠️ 收到Notion API速率限制 (429)，将在 {retry_after} 秒后重试... (尝试 {attempt + 1}/{max_retries})")
                time.sleep(retry_after)
                continue  # 继续下一次循环以重试
            else:
                raise e  # 其他HTTP错误，直接抛出
        except requests.exceptions.RequestException as e:
            # 其他请求相关错误（如网络问题），直接抛出
            raise e
    raise Exception(f"达到 {max_retries} 次最大重试次数后，请求仍然失败。")


def _extract_image_token(url: str) -> str:
    """从原始URL中提取核心图片Token。"""
    if not url:
        return ""
    # 示例: http://.../abc/notes_pre_post/123!xyz -> notes_pre_post/123
    try:
        return "/".join(url.split("/")[5:]).split("!")[0]
    except IndexError:
        return ""


def _generate_formatted_url(token: str, format_: str = "png") -> str:
    """根据Token和指定格式，生成新的、纯净的图片URL。"""
    if not token:
        return ""
    # 使用小红书的图片处理服务域名
    return f"https://ci.xiaohongshu.com/{token}?imageView2/format/{format_}"


def get_user_url(user_id: str, token: str = "") -> str:
    """根据用户ID和token生成小红书作者主页的URL。"""
    if not user_id:
        return ""
    base_url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
    if token:
        return f"{base_url}?xsec_token={token}"
    return base_url


def ensure_https(url):
    # 解析 URL 为各个组件
    parsed = urlparse(url)

    # 如果协议不是 https，将其改为 https
    if parsed.scheme != 'https':
        # 只修改协议部分，保持其他部分不变
        secure_parts = ('https',) + parsed[1:]
        secure_url = urlunparse(secure_parts)
        return secure_url

    # 如果已经是 https，直接返回原 URL
    return url


class NotionApi:
    def __init__(self):
        self.client = None
        self.database_id = None
        self.notion_token = None

    def _upload_image_direct(self, original_url: str):
        """
        【新功能】直接使用小红书的URL，通过Notion上传接口导入一张图片。
        返回成功上传后的Notion永久链接。
        """
        if not original_url:
            return None
        # 如果不是 https，则转换为 https

        https_url = ensure_https(original_url)
        print(https_url)
        headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Notion-Version": "2022-06-28"
        }
        try:
            # Step 1: Start the file upload
            upload_payload = {
                "mode": "external_url",
                "filename": "image.jpeg",
                "external_url": https_url
            }
            upload_response = _make_request_with_retry(
                'post',
                'https://api.notion.com/v1/file_uploads',
                headers={**headers, "Content-Type": "application/json"},
                data=json.dumps(upload_payload),
                timeout=15
            )
            response_data = upload_response.json()
            file_upload_id = response_data.get("id")
            if not file_upload_id:
                return None, "启动上传任务失败：未在响应中找到 file_upload_id。"

        except requests.exceptions.HTTPError as e:
            error_details = e.response.json()
            error_message = error_details.get("message", "未知API错误")
            return None, f"调用上传接口失败: {error_message} (状态码: {e.response.status_code})"
        except Exception as e:
            return None, f"启动上传任务时发生未知错误: {e}"

        # Step 2: Poll for completion
        max_poll_retries = 30
        for _ in range(max_poll_retries):
            try:
                status_url = f"https://api.notion.com/v1/file_uploads/{file_upload_id}"
                status_response = _make_request_with_retry('get', status_url, headers=headers)

                status_data = status_response.json()
                status = status_data.get("status")

                if status == "uploaded":
                    return file_upload_id, None
                if status == "failed":
                    error_info = status_data.get("file_import_result", {}).get("error", {})
                    return None, f"Notion服务器处理文件失败: {error_info.get('message', '未知上传失败原因')}"

                time.sleep(2)  # 等待2秒后再次查询
            except Exception as e:
                return None, f"查询上传状态时发生未知错误: {e}"

        return None, "上传超时：在规定时间内未完成上传。"

    def save_xiaohongshu_note_to_notion(
            self,
            notion_token: str,
            database_id: str,
            cookies_str: str,
            note_url: str = "",
            remarks: str = "",
            custom_tags: str = "",
            proxies: Optional[dict] = None,
    ) -> Tuple[bool, str, Optional[str]]:  # 修改返回类型
        # --- 1. 初始化客户端和基本校验 ---
        if not notion_token or not database_id:
            return False, "必须提供 Notion Token 和 Database ID", None  # 修改返回值格式

        try:
            notion = Client(auth=notion_token)
            self.client = notion
            self.notion_token = notion_token
            self.database_id = database_id
        except Exception as e:
            return False, f"初始化Notion客户端失败: {e}", None

        if not cookies_str:
            return False, "未设置Cookie", None
        xhs_apis = XHS_Apis()
        success, msg, api_response = xhs_apis.get_note_info(note_url, cookies_str, proxies)
        if not success:
            return False, f"获取笔记信息失败: {msg}", None

        # 修改后的API响应检查
        if not api_response.get("success") or not api_response.get("data", {}).get("items"):
            return False, "API响应无效或不包含笔记项目", None

        # --- 2. 解析和提取数据 ---
        note_card = api_response["data"]["items"][0].get("note_card")
        if not note_card:
            return False, "在API响应中未找到 'note_card' 数据。", None

        title = note_card.get("title", "无标题笔记")
        description = note_card.get("desc", "")
        # 提取作者信息和token
        user_info = note_card.get("user", {})
        author_name = user_info.get("nickname", "未知作者")
        author_id = user_info.get("user_id")
        xsec_token = user_info.get("xsec_token", "")

        # 【修改处】生成链接时传入token
        author_homepage_url = get_user_url(author_id, xsec_token)
        orign_link = note_url
        if "笔记" in note_url:
            orign_link = extract_url(note_url)
            orign_link = get_redirect_url(orign_link)
        note_link = orign_link

        interact_info = note_card.get("interact_info", {})
        # 点赞数可能会有 万这样的后缀，需要处理
        liked_count_orign = interact_info.get("liked_count", 0)
        if isinstance(liked_count_orign, str) and liked_count_orign.endswith("万"):
            liked_count = int(float(liked_count_orign[:-1]) * 10000)
        else:
            liked_count = int(liked_count_orign)
        collected_count_orign = interact_info.get("collected_count", 0)
        if isinstance(collected_count_orign, str) and collected_count_orign.endswith("万"):
            collected_count = int(float(collected_count_orign[:-1]) * 10000)
        else:
            collected_count = int(collected_count_orign)

        cover_url = ""
        if image_list := note_card.get("image_list"):
            cover_url = image_list[0].get("url_default", "")

        note_tags = [{"name": tag["name"]} for tag in note_card.get("tag_list", [])]

        video_url = ""
        if note_card.get("type") == "video" and (video_data := note_card.get("video")):
            if h264_streams := video_data.get("media", {}).get("stream", {}).get("h264", []):
                video_url = h264_streams[0].get("master_url", "")

        publish_date_iso = ""
        if publish_timestamp := note_card.get("time"):
            publish_date_iso = datetime.fromtimestamp(publish_timestamp / 1000).isoformat()

        # --- 3. 构建Notion API请求体 ---
        properties_payload = {
            "笔记标题": {"title": [{"text": {"content": title}}]},
            "描述or正文": {"rich_text": [{"text": {"content": description}}]},
            "笔记链接": {"url": note_link},
            "作者": {"rich_text": [{"text": {"content": author_name}}]},
            "笔记标签": {"multi_select": note_tags},
            "点赞数": {"number": liked_count},
            "收藏数": {"number": collected_count},
        }

        if author_homepage_url:
            properties_payload["作者主页"] = {"url": author_homepage_url}
        if video_url:
            properties_payload["视频链接"] = {"url": video_url}
        if publish_date_iso:
            properties_payload["发布时间"] = {"date": {"start": publish_date_iso}}
        custom_tags_list = custom_tags.split(",")
        if custom_tags_list and custom_tags_list[0] != "":
            properties_payload["自定义标签"] = {"multi_select": [{"name": tag} for tag in custom_tags_list]}
        if remarks:
            properties_payload["备注"] = {"rich_text": [{"text": {"content": remarks}}]}
        children_payload: List[Dict] = []
        if description:
            children_payload.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": description}
                    }],
                    "icon": {"emoji": "📝"}
                }
            })
        image_urls_to_upload = [_generate_formatted_url(_extract_image_token(img.get("url_default"))) for img in
                                image_list if img.get("url_default")]

        if image_urls_to_upload:
            print(f"开始并发处理 {len(image_urls_to_upload)} 张图片上传...")
            results = {}
            # 【修改处】将max_workers设置为3，以符合Notion的速率限制
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_to_url = {executor.submit(self._upload_image_direct, url): url for url in image_urls_to_upload}

                for future in concurrent.futures.as_completed(future_to_url):
                    original_url = future_to_url[future]
                    try:
                        notion_url, error = future.result()
                        if error:
                            print(f"❌ 图片上传失败: {original_url} -> 错误: {error}")
                            results[original_url] = None
                        else:
                            print(f"✅ 图片上传成功: {original_url}")
                            results[original_url] = notion_url
                    except Exception as exc:
                        print(f"❌ 图片上传时产生严重异常: {original_url} -> {exc}")
                        results[original_url] = None

            for image in image_urls_to_upload:
                if notion_image_url := results.get(image):
                    children_payload.append({
                        "object": "block", "type": "image",
                        "image": {"type": "file_upload", "file_upload": {"id": notion_image_url}}
                    })
        if video_url:
            children_payload.append({
                "object": "block",
                "type": "embed",
                "embed": {
                    "url": video_url
                }
            })
        # --- 优化结束 ---

        # --- 4. 调用Notion API创建页面并返回结果 ---
        try:
            if cover_url:
                new_page = notion.pages.create(
                    parent={"database_id": database_id},
                    properties=properties_payload,
                    children=children_payload if children_payload else None,
                    cover={"type": "external", "external": {"url": cover_url}}
                )
                return True, "成功创建页面", new_page.get("url")
            else:
                new_page = notion.pages.create(
                    parent={"database_id": database_id},
                    properties=properties_payload
                )
                return True, "成功创建页面", new_page.get("url")
        except APIResponseError as e:
            error_details = json.loads(e.body)
            error_message = error_details.get("message", "未知API错误")

            return False, f"Notion API 错误: {error_message} (代码: {e.code})", None  # 修改返回值格式
        except Exception as e:
            return False, f"发生未知错误: {e}", None


# --- 5. 如何调用此函数的示例 ---
if __name__ == "__main__":
    my_notion_token = "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"
    my_database_id = "20d8a47fcb1e8074948fe9845867a551"
    notion_api = NotionApi()
    my_custom_tags = "副业思考经验分享"
    my_remarks = "这篇笔记提到了放弃副业后的心态变化，对我很有启发。"
    if my_notion_token != "YOUR_NOTION_TOKEN" and my_database_id != "YOUR_DATABASE_ID":
        success, message, res = notion_api.save_xiaohongshu_note_to_notion(
            notion_token=my_notion_token,
            database_id=my_database_id,
            cookies_str="abRequestId=9872f025-e0df-5a1a-96d9-c784bd150b62; webBuild=4.63.0; a1=1970cd724bcox347lmqpm1lqd5p2hfjvp0depqg6w50000180463; webId=56fe9f62c3e2e4a78458879062e8f562; acw_tc=0a0bb41417482671179292571e22bd4ec644cb421d68c070661d3c38670f59; gid=yjW8SfWqDDU8yjW8SfWJ48AkDSlCq4W16AU6fKEy1Af2Ud28JxiVhU888yY84Kq8J4iKq84f; web_session=040069b973301279b886ea38013a4b9068c8be; unread={%22ub%22:%2268240d5c000000002100c89a%22%2C%22ue%22:%22682761f600000000120058f0%22%2C%22uc%22:26}; customer-sso-sid=68c517508750238543146546loaq0a7a2abvs9ay; x-user-id-creator.xiaohongshu.com=6807735a000000000a03e8d0; customerClientId=836094898645471; access-token-creator.xiaohongshu.com=customer.creator.AT-68c517508750238542964104sbybdodpqslpn7vy; galaxy_creator_session_id=V8qGqIwGCtgmUfmWwC26uunL9pt3YaH5bqW1; galaxy.creator.beaker.session.id=1748267151196073085102; xsecappid=xhs-pc-web; loadts=1748268715643; websectiga=16f444b9ff5e3d7e258b5f7674489196303a0b160e16647c6c2b4dcb609f4134; sec_poison_id=fc8e8503-1c33-406c-ac04-d94f12b5576b",
            note_url="33 快乐小狗钱女士发布了一篇小红书笔记，快来看吧！ 😆 VTv5KAZSWVDwqi1 😆 http://xhslink.com/a/wf5NMyBgULveb，复制本条信息，打开【小红书】App查看精彩内容！",
            custom_tags=my_custom_tags,
            remarks=my_remarks
        )
        if success:
            print(f"✅ 成功添加到Notion页面，链接为: {res}")
        else:
            print("请在 `if __name__ == '__main__':` 代码块中填入你的 Notion Token 和 Database ID。")
