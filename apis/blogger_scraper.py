import json
import random
import time
import uuid
from datetime import datetime

import psycopg2
from fastapi import HTTPException, BackgroundTasks
from loguru import logger

from apis.xhs_pc_apis import XHS_Apis


def _close_db_for_task_status(conn):
    """
    关闭用于更新任务状态的数据库连接
    """
    if conn:
        conn.close()


def _call_api_with_retry(api_func, *args, cookies_list=None, max_retries=3, **kwargs):
    """
    使用重试机制调用API，失败时尝试使用其他cookies

    Args:
        api_func (function): 要调用的API函数
        *args: API函数的位置参数
        cookies_list (list): cookies字符串列表
        max_retries (int): 最大重试次数
        **kwargs: API函数的关键字参数

    Returns:
        tuple: (success, msg, data) 成功标志、消息和数据
    """
    if not cookies_list or len(cookies_list) == 0:
        return False, "没有可用的cookies", None

    # 随机打乱cookies列表顺序
    random.shuffle(cookies_list)

    # 尝试使用不同的cookies调用API
    errors = []
    for i in range(min(max_retries, len(cookies_list))):
        try:
            cookies_str = cookies_list[i]
            # 替换args中的cookies参数
            new_args = list(args)
            for j, arg in enumerate(new_args):
                if isinstance(arg, str) and ('a1=' in arg or 'web_session=' in arg):
                    new_args[j] = cookies_str
                    break

            # 调用API
            success, msg, data = api_func(*new_args, **kwargs)
            if success:
                return success, msg, data
            else:
                errors.append(f"尝试 {i+1}/{max_retries} 失败: {msg}")
        except Exception as e:
            errors.append(f"尝试 {i+1}/{max_retries} 异常: {str(e)}")
        finally:
            # 每次尝试后随机暂停一段时间，避免请求过快
            time.sleep(random.uniform(1, 3))

    # 所有尝试都失败
    return False, f"所有尝试都失败: {'; '.join(errors)}", None


class BloggerScraperAPI:
    """
    小红书单博主笔记采集服务API模块
    该模块用于采集指定小红书博主的所有新增笔记，并将数据存入PostgreSQL数据库
    支持多cookies随机使用和失败重试机制
    """
    
    def __init__(self):
        """
        初始化博主笔记采集器API
        """
        import os
        from dotenv import load_dotenv
        load_dotenv()
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'dbname': os.getenv('DB_NAME', 'xhs_spider'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '')
        }
        self.xhs_apis = XHS_Apis()
        self.conn = None
        self.cursor = None
    
    def _connect_db(self):
        """
        连接到PostgreSQL数据库
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self.conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                dbname=self.db_config['dbname'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            return False
    
    def _close_db(self):
        """
        关闭数据库连接
        """
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def _connect_db_for_task_status(self):
        """
        连接到PostgreSQL数据库，用于更新任务状态
        """
        try:
            conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                dbname=self.db_config['dbname'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            conn.autocommit = True  # 自动提交，确保状态更新立即生效
            return conn
        except Exception as e:
            logger.error(f"数据库连接失败 (任务状态): {str(e)}")
            return None

    def _update_task_status(self, task_id, status, user_id=None, result_summary=None, error_details=None):
        """
        更新任务状态到数据库
        """
        conn = None
        try:
            conn = self._connect_db_for_task_status()
            if not conn:
                return

            cursor = conn.cursor()
            if status == "PENDING" or status == "RUNNING":
                sql = """
                INSERT INTO scraper_tasks (task_id, user_id, status, start_time)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (task_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    start_time = EXCLUDED.start_time,
                    end_time = NULL,
                    result_summary = NULL,
                    error_details = NULL;
                """
                cursor.execute(sql, (task_id, user_id, status))
            elif status == "COMPLETED":
                sql = """
                UPDATE scraper_tasks SET
                    status = %s,
                    end_time = CURRENT_TIMESTAMP,
                    result_summary = %s,
                    error_details = NULL
                WHERE task_id = %s;
                """
                cursor.execute(sql, (status, json.dumps(result_summary), task_id))
            elif status == "FAILED":
                sql = """
                UPDATE scraper_tasks SET
                    status = %s,
                    end_time = CURRENT_TIMESTAMP,
                    error_details = %s,
                    result_summary = NULL
                WHERE task_id = %s;
                """
                cursor.execute(sql, (status, error_details, task_id))
            conn.commit()
        except Exception as e:
            logger.error(f"更新任务状态失败 (task_id: {task_id}, status: {status}): {str(e)}")
        finally:
            _close_db_for_task_status(conn)

    def _call_blogger_details_api(self, user_id, cookies_list):
        """
        调用API获取博主详细信息
        
        Args:
            user_id (str): 博主ID
            cookies_list (list): cookies字符串列表
            
        Returns:
            tuple: (success, msg, data) 成功标志、消息和数据
        """
        return _call_api_with_retry(self.xhs_apis.get_user_info, user_id, cookies_list[0], cookies_list=cookies_list)
    
    def _call_all_notes_api(self, user_id, cookies_list):
        """
        调用API获取博主所有笔记列表
        
        Args:
            user_id (str): 博主ID
            cookies_list (list): cookies字符串列表
            
        Returns:
            tuple: (success, msg, data) 成功标志、消息和数据
        """
        # 构造用户URL
        user_url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
        return _call_api_with_retry(self.xhs_apis.get_user_all_notes, user_url, cookies_list[0], cookies_list=cookies_list)
    
    def _call_note_details_api(self, note_id, xsec_token, cookies_list):
        """
        调用API获取单篇笔记详细内容
        
        Args:
            note_id (str): 笔记ID
            xsec_token (str): xsec_token
            cookies_list (list): cookies字符串列表
            
        Returns:
            tuple: (success, msg, data) 成功标志、消息和数据
        """
        # 构造笔记URL
        note_url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}"
        return _call_api_with_retry(self.xhs_apis.get_note_info, note_url, cookies_list[0], cookies_list=cookies_list)
    
    def _save_blogger_info(self, user_id, blogger_info):
        """
        将博主信息存入数据库
        
        Args:
            user_id (str): 博主ID
            blogger_info (dict): 博主信息
            
        Returns:
            bool: 是否成功
        """
        try:
            # 从API返回的数据中提取需要的字段
            basic_info = blogger_info.get('basic_info', {})
            nickname = basic_info.get('nickname', '')
            avatar = basic_info.get('imageb', '')
            red_id = basic_info.get('red_id', '')
            gender = basic_info.get('gender', 2)  # 0男，1女，2未知
            gender_str = '男' if gender == 0 else '女' if gender == 1 else '未知'
            location = basic_info.get('ip_location', '')
            description = basic_info.get('desc', '')
            
            # 获取关注数、粉丝数等信息并转换为整数
            interactions = blogger_info.get('interactions', [])
            follows = self._convert_count_to_int(interactions[0].get('count', 0)) if len(interactions) > 0 else 0
            fans = self._convert_count_to_int(interactions[1].get('count', 0)) if len(interactions) > 1 else 0
            likes = self._convert_count_to_int(interactions[2].get('count', 0)) if len(interactions) > 2 else 0
            notes_count = 0  # 这个字段需要从笔记列表中获取

            sql = """
            INSERT INTO users (user_id, nickname, avatar, created_at, updated_at,
                              fans_count, likes_collections_count, notes_count, location, description)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                nickname = EXCLUDED.nickname,
                avatar = EXCLUDED.avatar,
                fans_count = EXCLUDED.fans_count,
                likes_collections_count = EXCLUDED.likes_collections_count,
                notes_count = EXCLUDED.notes_count,
                location = EXCLUDED.location,
                description = EXCLUDED.description,
                updated_at = CURRENT_TIMESTAMP;
            """
            logger.debug(f"Executing SQL: {sql}")
            logger.debug(f"With parameters: {user_id, nickname, avatar, fans, likes, notes_count, location, description}")
            self.cursor.execute(sql, (
                user_id, nickname, avatar, fans, likes, notes_count, location, description
            ))
            logger.debug(f"SQL execution result: rowcount = {self.cursor.rowcount}")
            self.cursor.connection.commit()
                
            return True
        except Exception as e:
            logger.error(f"保存博主信息失败: {str(e)}")
            return False
    
    def _get_existing_notes(self, user_id):
        """
        获取数据库中已存在的该博主的笔记ID列表
        
        Args:
            user_id (str): 博主ID
            
        Returns:
            list: 笔记ID列表
        """
        try:
            sql = "SELECT note_id FROM notes WHERE user_id = %s"
            self.cursor.execute(sql, (user_id,))
            results = self.cursor.fetchall()
            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"获取已存在笔记失败: {str(e)}")
            return []
    
    def _convert_count_to_int(self, count_str):
        """
        将包含单位（万、亿等）的数字字符串转换为整数
        
        Args:
            count_str (str): 数字字符串，如 "1.4万"、"2.3亿"、"500"
            
        Returns:
            int: 转换后的整数值
        """
        if not count_str:
            return 0
            
        try:
            # 尝试直接转换为整数
            return int(count_str)
        except ValueError:
            # 如果包含单位，需要特殊处理
            try:
                if '万' in count_str:
                    # 例如 "1.4万" -> 14000
                    num = float(count_str.replace('万', ''))
                    return int(num * 10000)
                elif '亿' in count_str:
                    # 例如 "1.2亿" -> 120000000
                    num = float(count_str.replace('亿', ''))
                    return int(num * 100000000)
                else:
                    # 其他情况，尝试去除非数字字符
                    import re
                    num_str = re.sub(r'[^\d.]', '', count_str)
                    return int(float(num_str)) if num_str else 0
            except Exception:
                logger.warning(f"无法转换数字: {count_str}，使用默认值0")
                return 0
    
    def _save_note_success(self, note_data):
        """
        将成功采集的笔记信息存入数据库
        
        Args:
            note_data (dict): 笔记数据
            
        Returns:
            bool: 是否成功
        """
        try:
            # 从API返回的数据中提取需要的字段
            note_id = note_data.get('note_id', '')
            user_id = note_data.get('user', {}).get('user_id', '')
            title = note_data.get('title', '')
            desc = note_data.get('desc', '')
            note_type_str = note_data.get('type', 'normal')
            note_type = 'video' if note_type_str == 'video' else 'normal'
            
            # 获取交互数据并转换为整数
            interact_info = note_data.get('interact_info', {})
            liked_count = self._convert_count_to_int(interact_info.get('liked_count', '0'))
            collected_count = self._convert_count_to_int(interact_info.get('collected_count', '0'))
            comments_count = self._convert_count_to_int(interact_info.get('comment_count', '0'))
            shared_count = self._convert_count_to_int(interact_info.get('share_count', '0'))
            
            # 获取图片和视频信息
            image_list = []
            video_url = ''
            cover_url = ''

            if note_type == 'normal':
                image_list = [img.get('url_default', '') for img in note_data.get('image_list', [])]
                if image_list:
                    cover_url = image_list[0]
            else:  # 视频
                stream_dict = note_data.get('video', {}).get('media', {}).get('stream', {})
                lowest_bitrate_stream = None
                if stream_dict:
                    all_streams = []
                    for format_streams in stream_dict.values():
                        all_streams.extend(format_streams)
                    
                    if all_streams:
                        # 寻找码率最低的视频流
                        lowest_bitrate_stream = min(all_streams, key=lambda x: x.get('bitrate', float('inf')))
                
                if lowest_bitrate_stream:
                    video_url = lowest_bitrate_stream.get('master_url', '')

                # 视频的封面图也在image_list里
                image_info = note_data.get('image_list', [])
                if image_info:
                    cover_url = image_info[0].get('url_default', '')
                    image_list.append(cover_url)

            # 获取时间和URL信息
            publish_time_raw = note_data.get('time', None) # 获取原始值，可能是整数或None
            publish_time = None
            if publish_time_raw is not None:
                try:
                    # 假设是Unix时间戳（毫秒），转换为秒
                    publish_time = datetime.fromtimestamp(publish_time_raw / 1000)
                except (TypeError, ValueError):
                    logger.warning(f"无法转换publish_time: {publish_time_raw}，使用None")
                    publish_time = datetime.now()
            note_url = f"https://www.xiaohongshu.com/explore/{note_id}"

            logger.debug(f"DEBUG: note_data type: {type(note_data)}, first 100 chars: {str(note_data)[:100]}")
            logger.debug(f"DEBUG: image_list type: {type(image_list)}, first 100 chars: {str(image_list)[:100]}")


            sql = """
            INSERT INTO notes (note_id, user_id, type, title, liked_count, comments_count,
                              collected_count, shared_count, cover_url, video_url, nick_name,
                              url, raw_data, image_list, publish_time, last_update_time,
                              created_at, updated_at, collection_status, collection_error)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s, %s)
            ON CONFLICT (note_id) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                type = EXCLUDED.type,
                title = EXCLUDED.title,
                liked_count = EXCLUDED.liked_count,
                comments_count = EXCLUDED.comments_count,
                collected_count = EXCLUDED.collected_count,
                shared_count = EXCLUDED.shared_count,
                cover_url = EXCLUDED.cover_url,
                video_url = EXCLUDED.video_url,
                nick_name = EXCLUDED.nick_name,
                url = EXCLUDED.url,
                raw_data = EXCLUDED.raw_data,
                image_list = EXCLUDED.image_list,
                publish_time = EXCLUDED.publish_time,
                last_update_time = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP,
                collection_status = EXCLUDED.collection_status,
                collection_error = EXCLUDED.collection_error;
            """
            self.cursor.execute(sql, (
                note_id, user_id, note_type, title, liked_count, comments_count,
                collected_count, shared_count, cover_url, video_url,
                note_data.get('user', {}).get('nickname', ''), note_url,
                json.dumps(note_data), json.dumps(image_list), publish_time,
                'success', None
            ))

            return True
        except Exception as e:
            logger.error(f"保存笔记信息失败: {str(e)}")
            return False
    
    def _save_note_failed(self, user_id, note_id, error_msg):
        """
        将采集失败的笔记信息存入数据库
        
        Args:
            user_id (str): 博主ID
            note_id (str): 笔记ID
            error_msg (str): 错误信息
            
        Returns:
            bool: 是否成功
        """
        pass

    
    def scrape_blogger_by_id(self, user_id, cookies_list, task_id):
        """
        采集指定博主的所有新增笔记
        
        Args:
            user_id (str): 博主ID
            cookies_list (list): Cookies字符串列表
            task_id (str): 任务ID
            
        Returns:
            dict: 包含详细执行统计和错误信息的JSON对象
        """
        # 初始化统计变量
        success_count = 0
        failed_count = 0
        error_details = []
        
        logger.info(f"开始采集博主 {user_id} 的笔记，任务ID: {task_id}")
        
        # 更新任务状态为运行中
        self._update_task_status(task_id, "RUNNING", user_id=user_id)
        
        # 连接数据库
        if not self._connect_db():
            error_msg = "数据库连接失败"
            self._update_task_status(task_id, "FAILED", error_details=error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "blogger_id": user_id,
                "stats": {
                    "online_notes_count": 0,
                    "new_notes_found": 0,
                    "successfully_saved": 0,
                    "failed_to_save": 0
                },
                "errors": []
            }
        
        try:
            # 开始事务
            self.conn.autocommit = False
            
            # 步骤2：获取并存储博主信息
            logger.info(f"[{task_id}] 正在获取博主 {user_id} 的信息...")
            success, msg, blogger_info = self._call_blogger_details_api(user_id, cookies_list)
            if not success:
                logger.error(f"[{task_id}] 获取博主 {user_id} 信息失败: {msg}")
                raise Exception(f"获取博主信息失败: {msg}")
            logger.info(f"[{task_id}] 成功获取博主 {user_id} 的信息，正在保存...")
            
            # 保存博主信息到数据库
            if not self._save_blogger_info(user_id, blogger_info['data']):
                logger.error(f"[{task_id}] 保存博主 {user_id} 信息到数据库失败")
                raise Exception("保存博主信息到数据库失败")
            logger.info(f"[{task_id}] 博主 {user_id} 信息保存成功。")
            
            # 步骤3：获取线上笔记列表
            logger.info(f"[{task_id}] 正在获取博主 {user_id} 的所有笔记列表...")
            success, msg, notes_list = self._call_all_notes_api(user_id, cookies_list)
            if not success:
                logger.error(f"[{task_id}] 获取博主 {user_id} 笔记列表失败: {msg}")
                raise Exception(f"获取博主笔记列表失败: {msg}")
            logger.info(f"[{task_id}] 成功获取博主 {user_id} 的 {len(notes_list)} 篇笔记列表。")
            
            # 提取所有笔记ID、xsec_token、title和nick_name
            online_notes_with_token = []
            for note in notes_list:
                note_id = note.get('note_id', '')
                xsec_token = note.get('xsec_token', '')
                title = note.get('title', '')  # 从笔记列表中获取title
                nick_name = note.get('user', {}).get('nickname', '') # 从笔记列表中获取nick_name
                if note_id:
                    online_notes_with_token.append((note_id, xsec_token, title, nick_name))
            
            # 步骤4：识别新增笔记
            existing_notes = self._get_existing_notes(user_id)
            new_note_ids_with_token = []
            for note_id, xsec_token, title, nick_name in online_notes_with_token:
                if note_id not in existing_notes:
                    new_note_ids_with_token.append((note_id, xsec_token, title, nick_name))
            logger.info(f"[{task_id}] 发现 {len(new_note_ids_with_token)} 篇新笔记需要采集。")
            
            # 步骤5：循环处理新增笔记
            for i, (note_id, xsec_token, initial_title, initial_nick_name) in enumerate(new_note_ids_with_token):
                logger.info(f"[{task_id}] ({i+1}/{len(new_note_ids_with_token)}) 正在获取笔记 {note_id} 详情...")
                # Initialize title and nick_name for the current iteration
                current_note_title = initial_title
                current_note_nick_name = initial_nick_name
                try:
                    # 5a. 获取笔记详情
                    success, msg, note_data_response = self._call_note_details_api(note_id, xsec_token, cookies_list)
                    if not success:
                        raise Exception(msg)
                    
                    logger.debug(f"DEBUG: Raw note_data_response for note {note_id}: {note_data_response}")

                    # 提取笔记数据
                    note_data = note_data_response['data']['items'][0]['note_card']
                    note_data['note_id'] = note_id



                    
                    # 5b. 存入成功记录
                    if self._save_note_success(note_data):
                        success_count += 1
                        logger.info(f"[{task_id}] 笔记 {note_id} 详情保存成功。")
                    else:
                        raise Exception("保存笔记数据到数据库失败")
                    
                except Exception as e:
                    # 5c. 捕获异常，处理失败
                    failed_count += 1
                    error_msg = str(e)
                    error_info = {"note_id": note_id, "error_message": error_msg}
                    error_details.append(error_info)
                    logger.error(f"[{task_id}] 笔记 {note_id} 采集失败: {error_msg}")
                    

            
            # 更新博主的笔记总数
            try:
                sql = "UPDATE users SET notes_count = %s WHERE user_id = %s"
                self.cursor.execute(sql, (len(online_notes_with_token), user_id))
                logger.info(f"[{task_id}] 博主 {user_id} 的笔记总数更新为 {len(online_notes_with_token)}。")
            except Exception as e:
                logger.warning(f"[{task_id}] 更新博主笔记总数失败: {str(e)}")

            # 步骤6：构建最终返回报告
            if failed_count == 0 and success_count > 0:
                status = "total_success"
            elif failed_count > 0 and success_count > 0:
                status = "partial_success"
            elif failed_count > 0 and success_count == 0:
                status = "total_failure"
            else:  # failed_count == 0 and success_count == 0
                status = "no_new_notes"
            
            # 步骤7：结束流程
            logger.info(f"[{task_id}] Committing transaction...")
            self.conn.commit()
            logger.info(f"[{task_id}] Transaction committed successfully.")
            logger.info(f"[{task_id}] 采集任务完成。成功: {success_count} 篇，失败: {failed_count} 篇。")
            
            # 构建返回结果
            result = {
                "status": status,
                "message": self._generate_message(success_count, failed_count),
                "blogger_id": user_id,
                "stats": {
                    "online_notes_count": len(online_notes_with_token),
                    "new_notes_found": len(new_note_ids_with_token),
                    "successfully_saved": success_count,
                    "failed_to_save": failed_count
                },
                "errors": error_details
            }
            self._update_task_status(task_id, "COMPLETED", result_summary=result)
            return result
            
        except Exception as e:
            # 发生致命错误，回滚事务
            self.conn.rollback()
            error_msg = str(e)
            logger.error(f"[{task_id}] 采集任务发生致命错误: {error_msg}")
            self._update_task_status(task_id, "FAILED", error_details=error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "blogger_id": user_id,
                "stats": {
                    "online_notes_count": 0,
                    "new_notes_found": 0,
                    "successfully_saved": 0,
                    "failed_to_save": 0
                },
                "errors": []
            }
        finally:
            # 关闭数据库连接
            self._close_db()
    
    def _generate_message(self, success_count, failed_count):
        """
        生成人类可读的状态消息
        
        Args:
            success_count (int): 成功数量
            failed_count (int): 失败数量
            
        Returns:
            str: 状态消息
        """
        total = success_count + failed_count
        if total == 0:
            return "没有发现新笔记"
        elif failed_count == 0:
            return f"采集完成，{success_count}篇笔记全部采集成功"
        elif success_count == 0:
            return f"采集完成，{failed_count}篇笔记全部采集失败"
        else:
            return f"采集完成，{success_count}篇成功，{failed_count}篇失败"


def get_all_cookies():
    """
    通过API获取所有可用的cookies
    
    Returns:
        list: cookies字符串列表
    """
    import requests
    
    cookies_list = []
    try:
        response = requests.get(
            url="https://n8n.iftrue.com.cn/webhook/3e2cdc91-ccca-48c3-9384-65a79a316ffe",
            headers={
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Accept': '*/*',
                'Host': 'n8n.iftrue.com.cn',
                'Connection': 'keep-alive'
            }
        )
        response.raise_for_status()  # 如果请求失败则抛出HTTPError
        data = response.json()
        
        if 'data' in data and isinstance(data['data'], list):
            for item in data['data']:
                if 'cookies' in item:
                    cookies_list.append(item['cookies'])
                    
    except requests.exceptions.RequestException as e:
        logger.error(f"从API获取Cookies失败: {e}")
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"解析Cookies API响应失败: {e}")
        
    # 过滤掉空字符串
    cookies_list = [cookie for cookie in cookies_list if cookie.strip()]
    
    return cookies_list


def scrape_blogger_by_id_api(user_id: str, background_tasks: BackgroundTasks = None):
    """
    API接口：采集指定博主的所有新增笔记
    
    Args:
        user_id (str): 博主ID
        background_tasks (BackgroundTasks, optional): FastAPI的后台任务管理器
        
    Returns:
        dict: 包含任务启动状态的JSON对象
    """
    # 获取所有cookies
    cookies_list = get_all_cookies()
    if not cookies_list:
        raise HTTPException(status_code=500, detail="没有可用的cookies")
    
    # 创建采集器实例
    scraper = BloggerScraperAPI()
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 记录任务开始状态
    scraper._update_task_status(task_id, "PENDING", user_id=user_id)
    # scraper.scrape_blogger_by_id(user_id, cookies_list, task_id)
    
    # 将采集任务添加到后台
    if background_tasks:
        background_tasks.add_task(scraper.scrape_blogger_by_id, user_id, cookies_list, task_id)
        return {
            "status": "success",
            "message": "博主笔记采集任务已在后台启动",
            "blogger_id": user_id,
            "task_id": task_id
        }
    else:
        # 如果没有提供background_tasks（例如在测试环境中），则直接执行
        # 这种情况下，任务状态不会被跟踪
        result = scraper.scrape_blogger_by_id(user_id, cookies_list, task_id)
        return result