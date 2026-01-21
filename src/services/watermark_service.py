"""去水印服务模块

通过 Lambda 代理或直接请求获取 Sora 视频的无水印下载链接
"""
import re
import asyncio
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
        from curl_cffi.requests import AsyncSession
        from ..core.http_utils import get_random_fingerprint
        
        url = "https://auth.openai.com/oauth/token"
        payload = {
            "client_id": account.get('client_id', 'app_OHnYmJt5u1XEdhDUx0ig1ziv'),
            "grant_type": "refresh_token",
            "redirect_uri": "com.openai.sora://auth.openai.com/android/com.openai.sora/callback",
            "refresh_token": account['refresh_token']
        }
        
        async with AsyncSession() as session:
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
        from curl_cffi.requests import AsyncSession
        from ..core.http_utils import get_random_fingerprint
        
        api_url = f"https://sora.chatgpt.com/backend/project_y/post/{video_id}"
        
        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'oai-package-name': 'com.openai.sora',
            'authorization': f'Bearer {account["access_token"]}',
            'User-Agent': 'Sora/1.2025.308'
        }
        
        async with AsyncSession() as session:
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
        # 提取视频 ID
        if url_or_id.startswith('http') or 'sora.chatgpt.com' in url_or_id:
            video_id = self.extract_video_id(url_or_id)
            if not video_id:
                return {"success": False, "error": "无效的 Sora 链接格式"}
        else:
            video_id = url_or_id
        
        # 获取账号
        account = await self.get_next_account()
        if not account:
            return {"success": False, "error": "没有可用的去水印账号"}
        
        # 判断使用 Lambda 还是直接请求
        use_lambda = await self._should_use_lambda()
        
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
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
                
                return {"success": True, "download_link": download_link}
                
            except Exception as e:
                last_error = str(e)
                error_str = str(e).lower()
                
                # 检查是否是 401 错误，尝试刷新 token
                if '401' in error_str and account.get('refresh_token'):
                    try:
                        new_access, new_refresh = await self.refresh_token(account)
                        account['access_token'] = new_access
                        continue
                    except Exception as refresh_error:
                        last_error = f"Token 刷新失败: {refresh_error}"
                
                # 429 或 403 错误，切换账号重试
                if '429' in error_str or '403' in error_str:
                    if attempt < max_retries - 1:
                        account = await self.get_next_account()
                        if account:
                            await asyncio.sleep(1)
                            continue
                
                break
        
        # 记录失败
        await self.db.update_watermark_account_usage(account['id'], success=False)
        await self.db.add_watermark_log(account['id'], video_id, False, error_msg=last_error)
        
        return {"success": False, "error": last_error}


# 全局实例
watermark_service = WatermarkService()
