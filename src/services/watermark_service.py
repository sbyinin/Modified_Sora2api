"""去水印服务模块

通过 Lambda 代理或直接请求获取 Sora 视频的无水印下载链接
"""
import re
import asyncio
import errno
from typing import Optional, Dict, Any
from ..core.database import Database
from ..core.config import config
from ..core.logger import debug_logger


class WatermarkService:
    """去水印服务"""
    
    def __init__(self):
        self.db = Database()
        self._account_index = 0
        self._lock = asyncio.Lock()
        self._accounts_cache = None
        self._cache_time = 0
        self._cache_ttl = 10  # 缓存10秒
        self._lambda_manager = None
        self._session = None
        self._session_lock = asyncio.Lock()
        self._max_concurrency = self._normalize_int(config.watermark_free_max_concurrency, default=2)
        self._semaphore = asyncio.Semaphore(self._max_concurrency)

    def _normalize_int(self, value: Optional[int], default: int, minimum: int = 1) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return default
        return normalized if normalized >= minimum else default

    async def _get_session(self):
        from curl_cffi.requests import AsyncSession
        if self._session is not None:
            return self._session
        async with self._session_lock:
            if self._session is None:
                self._session = AsyncSession()
        return self._session

    async def close(self):
        """Close shared HTTP session"""
        if self._session is None:
            return
        async with self._session_lock:
            if self._session is not None:
                self._session.close()
                self._session = None

    def _is_fd_exhausted_error(self, exc: Exception) -> bool:
        if isinstance(exc, OSError) and getattr(exc, "errno", None) in (errno.EMFILE, errno.ENFILE):
            return True
        return "too many open files" in str(exc).lower()
    
    async def _get_lambda_manager(self):
        """获取 Lambda manager 实例"""
        if self._lambda_manager is None:
            from .lambda_manager import lambda_manager
            self._lambda_manager = lambda_manager
        return self._lambda_manager
    
    async def _should_use_lambda(self) -> bool:
        """判断是否使用 Lambda"""
        lambda_mgr = await self._get_lambda_manager()
        return await lambda_mgr.is_enabled()
    
    async def _get_enabled_accounts(self):
        """获取启用的账号（带缓存）"""
        import time
        now = time.time()
        
        if self._accounts_cache is None or now >= self._cache_time + self._cache_ttl:
            self._accounts_cache = await self.db.get_enabled_watermark_accounts()
            self._cache_time = now
        
        return self._accounts_cache
    
    def invalidate_cache(self):
        """清除缓存"""
        self._accounts_cache = None
        self._cache_time = 0
    
    async def get_next_account(self) -> Optional[Dict]:
        """轮询获取下一个可用账号"""
        accounts = await self._get_enabled_accounts()
        if not accounts:
            return None
        
        async with self._lock:
            self._account_index = self._account_index % len(accounts)
            account = accounts[self._account_index]
            self._account_index += 1
        
        return account
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """从 Sora 分享链接提取视频 ID
        
        支持格式:
        - https://sora.chatgpt.com/p/s_xxx
        - sora.chatgpt.com/p/s_xxx
        """
        match = re.search(r'sora\.chatgpt\.com/p/([a-zA-Z0-9_]+)', url)
        return match.group(1) if match else None
    
    async def refresh_token(self, account: Dict) -> tuple:
        """刷新账号的 access_token"""
        from ..core.http_utils import get_random_fingerprint
        
        url = "https://auth.openai.com/oauth/token"
        payload = {
            "client_id": account.get('client_id', 'app_OHnYmJt5u1XEdhDUx0ig1ziv'),
            "grant_type": "refresh_token",
            "redirect_uri": "com.openai.sora://auth.openai.com/android/com.openai.sora/callback",
            "refresh_token": account['refresh_token']
        }
        
        session = await self._get_session()
        response = await session.post(
            url,
            json=payload,
            timeout=20,
            impersonate=get_random_fingerprint()
        )
        response.raise_for_status()
        data = response.json()
        
        # 更新数据库
        await self.db.update_watermark_account_usage(
            account['id'],
            success=True,
            new_access_token=data['access_token'],
            new_refresh_token=data['refresh_token']
        )
        
        self.invalidate_cache()
        return data['access_token'], data['refresh_token']
    
    async def _make_api_call_direct(self, video_id: str, account: Dict) -> Dict:
        """直接请求 Sora API"""
        from ..core.http_utils import get_random_fingerprint
        
        api_url = f"https://sora.chatgpt.com/backend/project_y/post/{video_id}"
        
        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'oai-package-name': 'com.openai.sora',
            'authorization': f'Bearer {account["access_token"]}',
            'User-Agent': 'Sora/1.2025.308'
        }
        
        session = await self._get_session()
        response = await session.get(
            api_url,
            headers=headers,
            timeout=20,
            impersonate=get_random_fingerprint()
        )
        response.raise_for_status()
        return response.json()
    
    async def _make_api_call_lambda(self, video_id: str, account: Dict) -> Dict:
        """通过 Lambda 代理请求"""
        lambda_mgr = await self._get_lambda_manager()
        
        return await lambda_mgr.make_request(
            token=account['access_token'],
            action="custom",
            method="GET",
            endpoint=f"/project_y/post/{video_id}",
            add_sentinel=False
        )
    
    async def get_download_link(self, url_or_id: str) -> Dict[str, Any]:
        """获取无水印下载链接
        
        Args:
            url_or_id: Sora 分享链接或视频 ID
            
        Returns:
            {
                "success": True/False,
                "download_link": "...",  # 成功时
                "error": "..."  # 失败时
            }
        """
        async with self._semaphore:
            return await self._get_download_link_inner(url_or_id)

    async def _get_download_link_inner(self, url_or_id: str) -> Dict[str, Any]:
        """获取无水印下载链接（内部实现）"""
        # 从数据库获取去水印配置
        watermark_config = await self.db.get_watermark_free_config()
        
        # 检查去水印功能是否启用
        if not watermark_config.watermark_free_enabled:
            return {"success": False, "error": "去水印功能未启用"}
        
        # 提取视频 ID
        if url_or_id.startswith('http') or 'sora.chatgpt.com' in url_or_id:
            video_id = self.extract_video_id(url_or_id)
            if not video_id:
                return {"success": False, "error": "无效的 Sora 链接格式"}
        else:
            video_id = url_or_id
        
        # 根据解析方式选择处理逻辑
        parse_method = watermark_config.parse_method
        debug_logger.log_info(f"使用解析方式: {parse_method}")
        
        if parse_method == "builtin":
            return await self._get_download_link_builtin(video_id)
        elif parse_method == "third_party":
            return {"success": False, "error": "第三方解析暂未实现，请使用内置解析"}
        elif parse_method == "custom":
            return await self._get_download_link_custom(video_id, watermark_config)
        else:
            return {"success": False, "error": f"不支持的解析方式: {parse_method}"}
    
    async def _get_download_link_builtin(self, video_id: str) -> Dict[str, Any]:
        """内置解析方式"""
        # 获取账号
        account = await self.get_next_account()
        if not account:
            return {"success": False, "error": "没有可用的去水印账号"}
        
        # 判断使用 Lambda 还是直接请求
        use_lambda = await self._should_use_lambda()
        
        max_retries = 5  # 增加重试次数
        last_error = None
        
        for attempt in range(max_retries):
            try:
                debug_logger.log_info(f"内置解析尝试 {attempt + 1}/{max_retries}, 视频ID: {video_id}, 账号: {account['id']}")
                
                # 发起请求
                if use_lambda:
                    response_data = await self._make_api_call_lambda(video_id, account)
                else:
                    response_data = await self._make_api_call_direct(video_id, account)
                
                # 提取下载链接
                download_link = response_data['post']['attachments'][0]['encodings']['source']['path']
                
                # 记录成功
                await self.db.update_watermark_account_usage(account['id'], success=True)
                await self.db.add_watermark_log(account['id'], video_id, True, download_link=download_link)
                
                debug_logger.log_info(f"内置解析成功，尝试次数: {attempt + 1}")
                return {"success": True, "download_link": download_link}
                
            except Exception as e:
                last_error = str(e)
                error_str = str(e).lower()
                debug_logger.log_error(f"内置解析失败 (尝试 {attempt + 1}): {last_error}")

                if self._is_fd_exhausted_error(e):
                    last_error = "Too many open files"
                    debug_logger.log_error("Detected local FD exhaustion, aborting watermark retries.")
                    break
                
                # 检查是否是 401 错误，尝试刷新 token
                if '401' in error_str and account.get('refresh_token'):
                    try:
                        debug_logger.log_info("检测到401错误，尝试刷新token")
                        new_access, new_refresh = await self.refresh_token(account)
                        account['access_token'] = new_access
                        await asyncio.sleep(0.5)  # 短暂延迟
                        continue
                    except Exception as refresh_error:
                        last_error = f"Token 刷新失败: {refresh_error}"
                        debug_logger.log_error(f"Token刷新失败: {refresh_error}")
                
                # 429 或 403 错误，切换账号重试
                if '429' in error_str or '403' in error_str:
                    if attempt < max_retries - 1:
                        debug_logger.log_info("检测到限流/权限错误，切换账号重试")
                        account = await self.get_next_account()
                        if account:
                            await asyncio.sleep(2)  # 增加延迟时间
                            continue
                        else:
                            last_error = "没有更多可用账号"
                            break
                
                # 网络错误等，短暂延迟后重试
                if any(keyword in error_str for keyword in ['timeout', 'connection', 'network']):
                    if attempt < max_retries - 1:
                        debug_logger.log_info("检测到网络错误，延迟后重试")
                        await asyncio.sleep(3)  # 网络错误延迟更长
                        continue
                
                # 其他错误，跳出循环
                break
        
        # 记录失败
        await self.db.update_watermark_account_usage(account['id'], success=False)
        await self.db.add_watermark_log(account['id'], video_id, False, error_msg=last_error)
        
        return {"success": False, "error": last_error}
    
    async def _get_download_link_custom(self, video_id: str, watermark_config) -> Dict[str, Any]:
        """自定义解析方式"""
        custom_url = watermark_config.custom_parse_url
        custom_token = watermark_config.custom_parse_token

        if not custom_url:
            return {"success": False, "error": "自定义解析服务器地址未配置"}

        if not custom_token:
            return {"success": False, "error": "自定义解析服务器访问密钥未配置"}

        from ..core.http_utils import get_random_fingerprint

        api_url = f"{custom_url.rstrip('/')}/parse"
        headers = {
            'Authorization': f'Bearer {custom_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'Sora2API/1.0'
        }
        payload = {
            'video_id': video_id,
            'url': f'https://sora.chatgpt.com/p/{video_id}'
        }

        max_retries = 9
        last_error = None
        session = await self._get_session()

        for attempt in range(1, max_retries + 1):
            try:
                debug_logger.log_info(f"自定义解析请求 (尝试 {attempt}/{max_retries}): {api_url}")
                response = await session.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=30,
                    impersonate=get_random_fingerprint()
                )
                response.raise_for_status()
                data = response.json()

                if data.get('success') and data.get('download_link'):
                    debug_logger.log_info(f"自定义解析成功，尝试次数: {attempt}")
                    return {"success": True, "download_link": data['download_link']}
                else:
                    last_error = data.get('error', '自定义解析服务返回失败')
                    debug_logger.log_error(f"自定义解析失败: {last_error}")
                    if attempt < max_retries:
                        wait = attempt * 2
                        debug_logger.log_info(f"等待 {wait}s 后重试...")
                        await asyncio.sleep(wait)

            except Exception as e:
                last_error = str(e)
                debug_logger.log_error(f"自定义解析请求异常 (尝试 {attempt}): {last_error}")
                if attempt < max_retries:
                    wait = attempt * 2
                    debug_logger.log_info(f"等待 {wait}s 后重试...")
                    await asyncio.sleep(wait)

        return {"success": False, "error": last_error}


# 全局实例
watermark_service = WatermarkService()
