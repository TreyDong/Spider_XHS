import requests
import json
import time
from typing import Optional, Tuple

def upload_external_file_to_notion(notion_token: str, external_url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    使用Notion官方上传接口，将一个外部URL的文件导入Notion，并返回其永久链接。
    本函数使用 requests 直接调用 HTTP API，并包含完整的轮询逻辑。

    :param notion_token: 您的Notion Integration Token。
    :param external_url: 您希望上传的原始文件链接。
    :return: 一个元组。成功时为 (Notion内部文件URL, None)，失败时为 (None, 错误信息字符串)。
    """
    # --- 准备通用请求头 ---
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28"
    }

    # --- 第一步: 开始文件上传 (Create a file upload) ---
    try:
        print(f"第一步: 开始上传任务，源链接: {external_url}")
        upload_payload = {
            "mode": "external_url",
            "filename": "image.jpeg",  # 文件名仅作标识，后缀有助于Notion识别
            "external_url": external_url
        }
        # 发送POST请求
        upload_response = requests.post(
            'https://api.notion.com/v1/file_uploads',
            headers={**headers, "Content-Type": "application/json"},
            data=json.dumps(upload_payload),
            timeout=15 # 设置超时
        )
        upload_response.raise_for_status() # 如果请求失败 (例如4xx, 5xx), 会抛出异常

        response_data = upload_response.json()
        file_upload_id = response_data.get("id")
        if not file_upload_id:
            return None, "启动上传任务失败：未在响应中找到 file_upload_id。"

        print(f"上传任务已创建，ID: {file_upload_id}")

    except requests.exceptions.HTTPError as e:
        # 捕获HTTP错误 (例如，URL预检查失败)
        error_details = e.response.json()
        error_message = error_details.get("message", "未知API错误")
        return None, f"调用上传接口失败: {error_message} (状态码: {e.response.status_code})"
    except Exception as e:
        return None, f"启动上传任务时发生未知错误: {e}"

    # --- 第二步: 轮询上传状态 (Poll for completion) ---
    max_retries = 15
    for i in range(max_retries):
        try:
            print(f"第二步: 第 {i+1}/{max_retries} 次查询上传状态...")
            status_url = f"https://api.notion.com/v1/file_uploads/{file_upload_id}"

            # GET请求不需要Content-Type
            status_response = requests.get(status_url, headers=headers, timeout=10)
            status_response.raise_for_status()

            status_data = status_response.json()
            status = status_data.get("status")
            print(f"    当前状态: {status}")

            if status == "uploaded":
                # 成功！返回Notion的内部文件链接
                notion_file_url = status_data.get("file", {}).get("url")
                return notion_file_url, None

            if status == "failed":
                # 上传失败，返回具体的失败原因
                error_info = status_data.get("file_import_result", {}).get("error", {})
                failure_message = error_info.get('message', '未知上传失败原因')
                return None, f"Notion服务器处理文件失败: {failure_message}"

            # 如果状态是pending，则等待后重试
            time.sleep(2)

        except requests.exceptions.HTTPError as e:
            error_details = e.response.json()
            error_message = error_details.get("message", "未知API错误")
            return None, f"查询状态时出错: {error_message} (状态码: {e.response.status_code})"
        except Exception as e:
            return None, f"查询状态时发生未知错误: {e}"

    # 如果循环结束仍未成功，则视为超时
    return None, "上传超时：在规定时间内未完成上传。"


# --- 测试入口 ---
if __name__ == "__main__":
    # --- 请在此处配置您的测试信息 ---
    # 1. 您的Notion集成令牌
    MY_NOTION_TOKEN = "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"

    # 2. 一张用于测试的小红书图片URL
    TEST_IMAGE_URL = "https://sns-webpic-qc.xhscdn.com/202506092025/1d24633294129e51f6f2e5769ca0320a/notes_pre_post/1040g3k831ifk2k66ges04a137smsln2s56djejg!nd_dft_wlteh_webp_3"


    print("--- 开始测试Notion文件上传模块 ---")

    if MY_NOTION_TOKEN == "YOUR_NOTION_TOKEN":
        print("\n❌ 错误: 请在脚本中填入您的真实NOTION_TOKEN。")
    else:
        # 调用上传函数
        final_url, error = upload_external_file_to_notion(
            notion_token=MY_NOTION_TOKEN,
            external_url=TEST_IMAGE_URL
        )

        # 打印最终结果
        print("\n--- 测试结果 ---")
        if error:
            print(f"❌ 上传失败: {error}")
        else:
            print(f"✅ 上传成功！")
            print(f"Notion内部永久链接: {final_url}")
            print("\n现在您可以在创建页面时，使用这个链接来添加图片块了。")
