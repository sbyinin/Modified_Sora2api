"""Lambda URL polling manager

Manages round-robin polling of multiple Lambda endpoints for video generation.
Provides a generic interface for all Sora API requests via Lambda.
"""
import asyncio
import errno
import httpx
import random
from typing import List, Optional, Dict, Any, Iterable
from ..core.database import Database
from ..core.models import LambdaConfig
from ..core.config import config


class LambdaManager:
    """Manages Lambda URL polling and load balancing"""
    
    def __init__(self):
        self.db = Database()
        self._current_index = 0
        self._lock = asyncio.Lock()
        self._config_cache: Optional[List[LambdaConfig]] = None
        self._cache_time = 0
        self._cache_ttl = 60  # Cache config for 60 seconds
        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()
        self._max_concurrency = self._normalize_int(config.lambda_max_concurrency, default=5, minimum=1)
        self._request_semaphore = asyncio.Semaphore(self._max_concurrency)
        self._limits = self._build_limits()
        self._timeout = self._normalize_float(config.lambda_timeout, default=30.0, minimum=1.0)
        self._retry_backoff_base = 0.5
        self._retry_backoff_max = 2.0

    def _normalize_int(self, value: Optional[int], default: int, minimum: int = 1) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return default
        return normalized if normalized >= minimum else default

    def _normalize_float(self, value: Optional[float], default: float, minimum: float = 0.0) -> float:
        try:
            normalized = float(value)
        except (TypeError, ValueError):
            return default
        return normalized if normalized >= minimum else default

    def _build_limits(self) -> httpx.Limits:
        max_connections = self._normalize_int(
            config.lambda_max_connections,
            default=max(self._max_concurrency * 2, 10),
            minimum=1
        )
        max_keepalive = self._normalize_int(
            config.lambda_max_keepalive_connections,
            default=min(max_connections, max(self._max_concurrency, 5)),
            minimum=1
        )
        keepalive_expiry = self._normalize_float(
            config.lambda_keepalive_expiry,
            default=20.0,
            minimum=1.0
        )
        return httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive,
            keepalive_expiry=keepalive_expiry
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        async with self._client_lock:
            if self._client is None:
                self._client = httpx.AsyncClient(
                    timeout=httpx.Timeout(self._timeout),
                    limits=self._limits
                )
        return self._client

    async def close(self):
        """Close shared HTTP client"""
        if self._client is None:
            return
        async with self._client_lock:
            if self._client is not None:
                await self._client.aclose()
                self._client = None

    def _iter_exception_chain(self, exc: BaseException) -> Iterable[BaseException]:
        current = exc
        seen = set()
        while current and id(current) not in seen:
            seen.add(id(current))
            yield current
            current = getattr(current, "__cause__", None) or getattr(current, "__context__", None)

    def _is_fd_exhausted_error(self, exc: BaseException) -> bool:
        for item in self._iter_exception_chain(exc):
            if isinstance(item, OSError) and getattr(item, "errno", None) in (errno.EMFILE, errno.ENFILE):
                return True
            if "too many open files" in str(item).lower():
                return True
        return False

    async def _backoff(self, attempt: int):
        delay = min(self._retry_backoff_base * (2 ** attempt), self._retry_backoff_max)
        jitter = random.uniform(0, self._retry_backoff_base)
        await asyncio.sleep(delay + jitter)

    async def _handle_retry(self, exc: Exception, attempt: int, total: int) -> bool:
        if self._is_fd_exhausted_error(exc):
            print("[Lambda] Local FD limit reached; aborting remaining endpoints.")
            return False
        if attempt < total - 1 and self._retry_backoff_base > 0:
            await self._backoff(attempt)
        return True
    
    async def _get_config(self) -> List[LambdaConfig]:
        """Get Lambda configuration with caching"""
        import time
        current_time = time.time()
        
        if (self._config_cache is None or 
            current_time - self._cache_time > self._cache_ttl):
            self._config_cache = await self.db.get_lambda_configs()
            self._cache_time = current_time
        
        return self._config_cache
    
    def _get_urls(self, configs: List[LambdaConfig]) -> List[str]:
        """Get enabled Lambda URLs from per-row configurations"""
        urls = []
        for cfg in configs:
            if not cfg.lambda_enabled:
                continue
            if not cfg.lambda_api_url:
                continue
            urls.append(cfg.lambda_api_url.strip())
        return urls

    def _get_endpoints(self, configs: List[LambdaConfig]) -> List[Dict[str, str]]:
        """Build endpoint list from per-row configurations (only enabled)"""
        endpoints = []
        for cfg in configs:
            if not cfg.lambda_enabled:
                continue
            if not cfg.lambda_api_url:
                continue
            api_key = cfg.lambda_api_key or ""
            if not api_key:
                continue
            endpoints.append({
                "url": cfg.lambda_api_url.strip(),
                "key": api_key
            })
        return endpoints
    
    def _get_all_endpoints(self, configs: List[LambdaConfig]) -> List[Dict[str, str]]:
        """Build endpoint list from all configurations (ignore enabled flag)
        
        Used for Lambda Only mode to get oai-did without enabling Lambda create.
        """
        endpoints = []
        for cfg in configs:
            if not cfg.lambda_api_url:
                continue
            api_key = cfg.lambda_api_key or ""
            if not api_key:
                continue
            endpoints.append({
                "url": cfg.lambda_api_url.strip(),
                "key": api_key
            })
        return endpoints
    
    async def get_next_endpoint(self) -> Optional[Dict[str, str]]:
        """Get next endpoint using round-robin polling"""
        configs = await self._get_config()
        endpoints = self._get_endpoints(configs)
        if not endpoints:
            return None

        async with self._lock:
            # Round-robin selection
            endpoint = endpoints[self._current_index % len(endpoints)]
            self._current_index = (self._current_index + 1) % len(endpoints)
            return endpoint
    
    async def get_api_key(self) -> Optional[str]:
        """Get a Lambda API key from the first available endpoint"""
        configs = await self._get_config()
        endpoints = self._get_endpoints(configs)
        return endpoints[0]["key"] if endpoints else None
    
    async def is_enabled(self) -> bool:
        """Check if Lambda is enabled"""
        configs = await self._get_config()
        return any(cfg.lambda_enabled for cfg in configs)
    
    async def get_all_urls(self) -> List[str]:
        """Get all configured URLs"""
        configs = await self._get_config()
        return self._get_urls(configs)

    async def has_available_endpoints(self) -> bool:
        """Check if there is any usable endpoint"""
        configs = await self._get_config()
        return bool(self._get_endpoints(configs))
    
    async def create_task(self, token: str, payload: Dict[str, Any]) -> str:
        """Create task using next available Lambda endpoint
        
        Args:
            token: Access token
            payload: Task creation payload
            
        Returns:
            Task ID from Lambda response
            
        Raises:
            HTTPException: If all endpoints fail or Lambda is disabled
        """
        from fastapi import HTTPException
        
        if not await self.is_enabled():
            raise HTTPException(status_code=400, detail="Lambda is not enabled")
        
        configs = await self._get_config()
        urls = self._get_urls(configs)
        if not urls:
            raise HTTPException(status_code=400, detail="No Lambda URLs configured")

        endpoints = self._get_endpoints(configs)
        if not endpoints:
            raise HTTPException(status_code=400, detail="Lambda API key not configured")
        
        # Try each URL in round-robin order
        last_error = None
        for attempt in range(len(endpoints)):
            endpoint = await self.get_next_endpoint()
            if not endpoint:
                continue
            
            try:
                task_id = await self._post_create_task(endpoint["url"], endpoint["key"], token, payload)
                print(f"✅ [Lambda] Task created successfully using {endpoint['url']}: {task_id}")
                return task_id
            except Exception as e:
                last_error = e
                print(f"⚠️ [Lambda] Failed to create task using {endpoint['url']}: {str(e)}")
                if not await self._handle_retry(e, attempt, len(endpoints)):
                    break
                continue
        
        # All endpoints failed
        error_msg = f"All Lambda endpoints failed. Last error: {str(last_error)}"
        print(f"❌ [Lambda] {error_msg}")
        raise HTTPException(status_code=502, detail=error_msg)
    
    async def _post_create_task(self, lambda_url: str, api_key: Optional[str],
                               token: str, payload: Dict[str, Any]) -> str:
        """Post task creation request to specific Lambda endpoint
        
        Args:
            lambda_url: Lambda endpoint URL
            api_key: Lambda API key
            token: Access token
            payload: Task creation payload
            
        Returns:
            Task ID from response
            
        Raises:
            Exception: If request fails or response is invalid
        """
        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["x-lambda-key"] = api_key
        
        request_data = {
            "token": token,
            "payload": payload
        }
        
        client = await self._get_client()
        async with self._request_semaphore:
            response = await client.post(
                lambda_url,
                json=request_data,
                headers=headers
            )
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")
        
        try:
            data = response.json()
        except Exception:
            raise Exception("Invalid JSON response")
        
        task_id = data.get("id") or data.get("task_id")
        if not task_id:
            raise Exception("No task ID in response")
        
        return task_id

    async def make_request(
        self,
        token: str,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
        method: Optional[str] = None,
        endpoint: Optional[str] = None,
        add_sentinel: Optional[bool] = None,
        flow: Optional[str] = None,
        user_agent: Optional[str] = None,
        oai_did: Optional[str] = None
    ) -> Dict[str, Any]:
        """通用 Lambda 请求方法
        
        通过 Lambda 代理发起任意 Sora API 请求
        
        Args:
            token: Access token
            action: 请求类型 (nf_create, pending, me, custom 等)
            payload: 请求体 (POST 请求)
            method: HTTP 方法 (仅 custom action 需要)
            endpoint: API 端点 (仅 custom action 需要)
            add_sentinel: 是否添加 sentinel token
            flow: sentinel flow 类型
            user_agent: 自定义 UA
            oai_did: oai-did cookie 值
            
        Returns:
            API 响应 (已解析的 JSON)
            
        Raises:
            HTTPException: If all endpoints fail or Lambda is disabled
        """
        from fastapi import HTTPException
        
        if not await self.is_enabled():
            raise HTTPException(status_code=400, detail="Lambda is not enabled")
        
        configs = await self._get_config()
        endpoints = self._get_endpoints(configs)
        if not endpoints:
            raise HTTPException(status_code=400, detail="Lambda API key not configured")
        
        # 构建请求数据
        request_data: Dict[str, Any] = {
            "token": token,
            "action": action,
        }
        
        if payload is not None:
            request_data["payload"] = payload
        if method is not None:
            request_data["method"] = method
        if endpoint is not None:
            request_data["endpoint"] = endpoint
        if add_sentinel is not None:
            request_data["add_sentinel"] = add_sentinel
        if flow is not None:
            request_data["flow"] = flow
        if user_agent is not None:
            request_data["user_agent"] = user_agent
        if oai_did is not None:
            request_data["oai_did"] = oai_did
        
        # Try each endpoint in round-robin order
        last_error = None
        for attempt in range(len(endpoints)):
            ep = await self.get_next_endpoint()
            if not ep:
                continue
            
            try:
                result = await self._post_request(ep["url"], ep["key"], request_data)
                print(f"✅ [Lambda] Request '{action}' succeeded using {ep['url']}")
                return result
            except Exception as e:
                last_error = e
                print(f"⚠️ [Lambda] Request '{action}' failed using {ep['url']}: {str(e)}")
                if not await self._handle_retry(e, attempt, len(endpoints)):
                    break
                continue
        
        # All endpoints failed
        error_msg = f"All Lambda endpoints failed. Last error: {str(last_error)}"
        print(f"❌ [Lambda] {error_msg}")
        raise HTTPException(status_code=502, detail=error_msg)

    async def _post_request(
        self,
        lambda_url: str,
        api_key: str,
        request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """发送请求到 Lambda 端点
        
        Args:
            lambda_url: Lambda endpoint URL
            api_key: Lambda API key
            request_data: 请求数据
            
        Returns:
            解析后的 JSON 响应
            
        Raises:
            Exception: If request fails or response is invalid
        """
        headers = {
            "Content-Type": "application/json",
            "x-lambda-key": api_key
        }

        client = await self._get_client()
        async with self._request_semaphore:
            response = await client.post(
                lambda_url,
                json=request_data,
                headers=headers
            )
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")
        
        try:
            return response.json()
        except Exception:
            raise Exception("Invalid JSON response")

    async def rt_to_at(self, refresh_token: str, client_id: Optional[str] = None) -> Dict[str, Any]:
        """通过 Lambda 将 Refresh Token 转换为 Access Token
        
        Args:
            refresh_token: Refresh Token
            client_id: Client ID (可选)
            
        Returns:
            包含 access_token, refresh_token, expires_in 的响应
            
        Raises:
            HTTPException: If all endpoints fail or Lambda is disabled
        """
        from fastapi import HTTPException
        
        if not await self.is_enabled():
            raise HTTPException(status_code=400, detail="Lambda is not enabled")
        
        configs = await self._get_config()
        endpoints = self._get_endpoints(configs)
        if not endpoints:
            raise HTTPException(status_code=400, detail="Lambda API key not configured")
        
        # 构建请求数据
        request_data: Dict[str, Any] = {
            "action": "rt_to_at",
            "refresh_token": refresh_token,
        }
        if client_id:
            request_data["client_id"] = client_id
        
        # Try each endpoint in round-robin order
        last_error = None
        for attempt in range(len(endpoints)):
            ep = await self.get_next_endpoint()
            if not ep:
                continue
            
            try:
                result = await self._post_request(ep["url"], ep["key"], request_data)
                print(f"✅ [Lambda] RT to AT succeeded using {ep['url']}")
                return result
            except Exception as e:
                last_error = e
                print(f"⚠️ [Lambda] RT to AT failed using {ep['url']}: {str(e)}")
                if not await self._handle_retry(e, attempt, len(endpoints)):
                    break
                continue
        
        # All endpoints failed
        error_msg = f"All Lambda endpoints failed. Last error: {str(last_error)}"
        print(f"❌ [Lambda] {error_msg}")
        raise HTTPException(status_code=502, detail=error_msg)

    async def st_to_at(self, session_token: str) -> Dict[str, Any]:
        """通过 Lambda 将 Session Token 转换为 Access Token
        
        Args:
            session_token: Session Token
            
        Returns:
            包含 accessToken 等信息的响应
            
        Raises:
            HTTPException: If all endpoints fail or Lambda is disabled
        """
        from fastapi import HTTPException
        
        if not await self.is_enabled():
            raise HTTPException(status_code=400, detail="Lambda is not enabled")
        
        configs = await self._get_config()
        endpoints = self._get_endpoints(configs)
        if not endpoints:
            raise HTTPException(status_code=400, detail="Lambda API key not configured")
        
        # 构建请求数据
        request_data: Dict[str, Any] = {
            "action": "st_to_at",
            "session_token": session_token,
        }
        
        # Try each endpoint in round-robin order
        last_error = None
        for attempt in range(len(endpoints)):
            ep = await self.get_next_endpoint()
            if not ep:
                continue
            
            try:
                result = await self._post_request(ep["url"], ep["key"], request_data)
                print(f"✅ [Lambda] ST to AT succeeded using {ep['url']}")
                return result
            except Exception as e:
                last_error = e
                print(f"⚠️ [Lambda] ST to AT failed using {ep['url']}: {str(e)}")
                if not await self._handle_retry(e, attempt, len(endpoints)):
                    break
                continue
        
        # All endpoints failed
        error_msg = f"All Lambda endpoints failed. Last error: {str(last_error)}"
        print(f"❌ [Lambda] {error_msg}")
        raise HTTPException(status_code=502, detail=error_msg)
    
    def invalidate_cache(self):
        """Invalidate configuration cache"""
        self._config_cache = None
        self._cache_time = 0


# Global instance
lambda_manager = LambdaManager()
