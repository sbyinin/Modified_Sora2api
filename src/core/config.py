"""Configuration management"""
import tomli
from pathlib import Path
from typing import Dict, Any, Optional

class Config:
    """Application configuration"""

    def __init__(self):
        self._config = self._load_config()
        self._admin_username: Optional[str] = None
        self._admin_password: Optional[str] = None
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from setting.toml"""
        config_path = Path(__file__).parent.parent.parent / "config" / "setting.toml"
        with open(config_path, "rb") as f:
            return tomli.load(f)

    def reload_config(self):
        """Reload configuration from file"""
        self._config = self._load_config()

    def get_raw_config(self) -> Dict[str, Any]:
        """Get raw configuration dictionary"""
        return self._config
    
    @property
    def admin_username(self) -> str:
        # If admin_username is set from database, use it; otherwise fall back to config file
        if self._admin_username is not None:
            return self._admin_username
        return self._config["global"]["admin_username"]

    @admin_username.setter
    def admin_username(self, value: str):
        self._admin_username = value
        self._config["global"]["admin_username"] = value

    def set_admin_username_from_db(self, username: str):
        """Set admin username from database"""
        self._admin_username = username

    @property
    def sora_base_url(self) -> str:
        return self._config["sora"]["base_url"]
    
    @property
    def sora_timeout(self) -> int:
        return self._config["sora"]["timeout"]
    
    @property
    def sora_max_retries(self) -> int:
        return self._config["sora"]["max_retries"]
    
    @property
    def poll_interval(self) -> float:
        return self._config["sora"]["poll_interval"]

    def set_poll_interval(self, interval: float):
        """Set task progress polling interval in seconds"""
        if "sora" not in self._config:
            self._config["sora"] = {}
        self._config["sora"]["poll_interval"] = float(interval)

    @property
    def max_poll_attempts(self) -> int:
        return self._config["sora"]["max_poll_attempts"]
    
    @property
    def server_host(self) -> str:
        return self._config["server"]["host"]
    
    @property
    def server_port(self) -> int:
        return self._config["server"]["port"]

    @property
    def debug_enabled(self) -> bool:
        return self._config.get("debug", {}).get("enabled", False)

    @property
    def debug_log_requests(self) -> bool:
        return self._config.get("debug", {}).get("log_requests", True)

    @property
    def debug_log_responses(self) -> bool:
        return self._config.get("debug", {}).get("log_responses", True)

    @property
    def debug_mask_token(self) -> bool:
        return self._config.get("debug", {}).get("mask_token", True)

    # Mutable properties for runtime updates
    @property
    def api_key(self) -> str:
        return self._config["global"]["api_key"]

    @api_key.setter
    def api_key(self, value: str):
        self._config["global"]["api_key"] = value

    @property
    def admin_password(self) -> str:
        # If admin_password is set from database, use it; otherwise fall back to config file
        if self._admin_password is not None:
            return self._admin_password
        return self._config["global"]["admin_password"]

    @admin_password.setter
    def admin_password(self, value: str):
        self._admin_password = value
        self._config["global"]["admin_password"] = value

    def set_admin_password_from_db(self, password: str):
        """Set admin password from database"""
        self._admin_password = password

    def set_debug_enabled(self, enabled: bool):
        """Set debug mode enabled/disabled"""
        if "debug" not in self._config:
            self._config["debug"] = {}
        self._config["debug"]["enabled"] = enabled

    @property
    def cache_timeout(self) -> int:
        """Get cache timeout in seconds"""
        return self._config.get("cache", {}).get("timeout", 7200)

    def set_cache_timeout(self, timeout: int):
        """Set cache timeout in seconds"""
        if "cache" not in self._config:
            self._config["cache"] = {}
        self._config["cache"]["timeout"] = timeout

    @property
    def cache_base_url(self) -> str:
        """Get cache base URL"""
        return self._config.get("cache", {}).get("base_url", "")

    def set_cache_base_url(self, base_url: str):
        """Set cache base URL"""
        if "cache" not in self._config:
            self._config["cache"] = {}
        self._config["cache"]["base_url"] = base_url

    @property
    def cache_enabled(self) -> bool:
        """Get cache enabled status"""
        return self._config.get("cache", {}).get("enabled", False)

    def set_cache_enabled(self, enabled: bool):
        """Set cache enabled status"""
        if "cache" not in self._config:
            self._config["cache"] = {}
        self._config["cache"]["enabled"] = enabled

    @property
    def cache_max_concurrency(self) -> int:
        """Get cache download max concurrency"""
        return self._config.get("cache", {}).get("max_concurrency", 3)

    @property
    def image_timeout(self) -> int:
        """Get image generation timeout in seconds"""
        return self._config.get("generation", {}).get("image_timeout", 300)

    def set_image_timeout(self, timeout: int):
        """Set image generation timeout in seconds"""
        if "generation" not in self._config:
            self._config["generation"] = {}
        self._config["generation"]["image_timeout"] = timeout

    @property
    def video_timeout(self) -> int:
        """Get video generation timeout in seconds"""
        return self._config.get("generation", {}).get("video_timeout", 1500)

    def set_video_timeout(self, timeout: int):
        """Set video generation timeout in seconds"""
        if "generation" not in self._config:
            self._config["generation"] = {}
        self._config["generation"]["video_timeout"] = timeout

    @property
    def watermark_free_enabled(self) -> bool:
        """Get watermark-free mode enabled status"""
        return self._config.get("watermark_free", {}).get("watermark_free_enabled", False)

    def set_watermark_free_enabled(self, enabled: bool):
        """Set watermark-free mode enabled/disabled"""
        if "watermark_free" not in self._config:
            self._config["watermark_free"] = {}
        self._config["watermark_free"]["watermark_free_enabled"] = enabled

    @property
    def watermark_free_parse_method(self) -> str:
        """Get watermark-free parse method"""
        return self._config.get("watermark_free", {}).get("parse_method", "builtin")

    @property
    def watermark_free_custom_url(self) -> str:
        """Get custom parse server URL"""
        return self._config.get("watermark_free", {}).get("custom_parse_url", "")

    @property
    def watermark_free_custom_token(self) -> str:
        """Get custom parse server access token"""
        return self._config.get("watermark_free", {}).get("custom_parse_token", "")

    @property
    def watermark_free_max_concurrency(self) -> int:
        """Get watermark-free flow max concurrency"""
        return self._config.get("watermark_free", {}).get("max_concurrency", 2)

    @property
    def watermark_free_fallback_on_failure(self) -> bool:
        """Get whether watermark-free mode falls back to watermarked output on failure"""
        return self._config.get("watermark_free", {}).get("fallback_on_failure", True)

    @property
    def at_auto_refresh_enabled(self) -> bool:
        """Get AT auto refresh enabled status"""
        return self._config.get("token_refresh", {}).get("at_auto_refresh_enabled", False)

    def set_at_auto_refresh_enabled(self, enabled: bool):
        """Set AT auto refresh enabled/disabled"""
        if "token_refresh" not in self._config:
            self._config["token_refresh"] = {}
        self._config["token_refresh"]["at_auto_refresh_enabled"] = enabled

    @property
    def polling_mode_enabled(self) -> bool:
        """Get polling mode enabled status"""
        return self.call_logic_mode == "polling"

    @property
    def call_logic_mode(self) -> str:
        """Get call logic mode (default or polling)"""
        call_logic = self._config.get("call_logic", {})
        mode = call_logic.get("call_mode")
        if mode in ("default", "polling"):
            return mode
        if call_logic.get("polling_mode_enabled", False):
            return "polling"
        return "default"

    def set_polling_mode_enabled(self, enabled: bool):
        """Set polling mode enabled/disabled"""
        self.set_call_logic_mode("polling" if enabled else "default")

    def set_call_logic_mode(self, mode: str):
        """Set call logic mode (default or polling)"""
        normalized = "polling" if mode == "polling" else "default"
        if "call_logic" not in self._config:
            self._config["call_logic"] = {}
        self._config["call_logic"]["call_mode"] = normalized
        self._config["call_logic"]["polling_mode_enabled"] = normalized == "polling"

    @property
    def timezone_offset(self) -> int:
        """Get configured timezone offset in hours"""
        return int(self._config.get("timezone", {}).get("timezone_offset", 8))

    @property
    def pow_service_mode(self) -> str:
        """Get POW service mode (local or external)"""
        return self._config.get("pow_service", {}).get("mode", "local")

    def set_pow_service_mode(self, mode: str):
        """Set POW service mode"""
        if "pow_service" not in self._config:
            self._config["pow_service"] = {}
        self._config["pow_service"]["mode"] = mode

    @property
    def pow_service_use_token_for_pow(self) -> bool:
        """Whether to use current token for POW calculation"""
        return self._config.get("pow_service", {}).get("use_token_for_pow", False)

    def set_pow_service_use_token_for_pow(self, enabled: bool):
        """Set whether to use current token for POW calculation"""
        if "pow_service" not in self._config:
            self._config["pow_service"] = {}
        self._config["pow_service"]["use_token_for_pow"] = enabled

    @property
    def pow_service_server_url(self) -> str:
        """Get POW service server URL"""
        return self._config.get("pow_service", {}).get("server_url", "")

    def set_pow_service_server_url(self, url: str):
        """Set POW service server URL"""
        if "pow_service" not in self._config:
            self._config["pow_service"] = {}
        self._config["pow_service"]["server_url"] = url

    @property
    def pow_service_api_key(self) -> str:
        """Get POW service API key"""
        return self._config.get("pow_service", {}).get("api_key", "")

    def set_pow_service_api_key(self, api_key: str):
        """Set POW service API key"""
        if "pow_service" not in self._config:
            self._config["pow_service"] = {}
        self._config["pow_service"]["api_key"] = api_key

    @property
    def pow_service_proxy_enabled(self) -> bool:
        """Get POW service proxy enabled status"""
        return self._config.get("pow_service", {}).get("proxy_enabled", False)

    def set_pow_service_proxy_enabled(self, enabled: bool):
        """Set POW service proxy enabled status"""
        if "pow_service" not in self._config:
            self._config["pow_service"] = {}
        self._config["pow_service"]["proxy_enabled"] = enabled

    @property
    def pow_service_proxy_url(self) -> str:
        """Get POW service proxy URL"""
        return self._config.get("pow_service", {}).get("proxy_url", "")

    def set_pow_service_proxy_url(self, url: str):
        """Set POW service proxy URL"""
        if "pow_service" not in self._config:
            self._config["pow_service"] = {}
        self._config["pow_service"]["proxy_url"] = url

    # ==================== Cloudflare Configuration ====================
    
    @property
    def cf_enabled(self) -> bool:
        """Get Cloudflare solver enabled status"""
        cf_config = self._config.get("cloudflare", {})
        # Support both 'enabled' and legacy 'solver_enabled'
        return cf_config.get("enabled", cf_config.get("solver_enabled", False))

    def set_cf_enabled(self, enabled: bool):
        """Set Cloudflare solver enabled/disabled"""
        if "cloudflare" not in self._config:
            self._config["cloudflare"] = {}
        self._config["cloudflare"]["enabled"] = enabled

    @property
    def cf_api_key(self) -> str:
        """Get Cloudflare solver API key"""
        return self._config.get("cloudflare", {}).get("api_key", "")

    def set_cf_api_key(self, key: str):
        """Set Cloudflare solver API key"""
        if "cloudflare" not in self._config:
            self._config["cloudflare"] = {}
        self._config["cloudflare"]["api_key"] = key

    @property
    def cf_api_url(self) -> str:
        """Get Cloudflare solver base URL (e.g., http://localhost:8000)"""
        cf_config = self._config.get("cloudflare", {})
        # Support both 'api_url' and legacy 'solver_api_url'
        return cf_config.get("api_url", cf_config.get("solver_api_url", "http://localhost:8000"))

    def set_cf_api_url(self, url: str):
        """Set Cloudflare solver base URL"""
        if "cloudflare" not in self._config:
            self._config["cloudflare"] = {}
        self._config["cloudflare"]["api_url"] = url

    @property
    def cf_global_enabled(self) -> bool:
        """Get Cloudflare global mode enabled (use CF for all requests)"""
        return self._config.get("cloudflare", {}).get("global_enabled", False)

    def set_cf_global_enabled(self, enabled: bool):
        """Set Cloudflare global mode enabled/disabled"""
        if "cloudflare" not in self._config:
            self._config["cloudflare"] = {}
        self._config["cloudflare"]["global_enabled"] = enabled

    @property
    def cf_api_only_enabled(self) -> bool:
        """Get Cloudflare API-only mode enabled (use CF only for API requests)"""
        return self._config.get("cloudflare", {}).get("api_only_enabled", True)

    def set_cf_api_only_enabled(self, enabled: bool):
        """Set Cloudflare API-only mode enabled/disabled"""
        if "cloudflare" not in self._config:
            self._config["cloudflare"] = {}
        self._config["cloudflare"]["api_only_enabled"] = enabled

    # ==================== Database Configuration ====================
    
    @property
    def db_type(self) -> str:
        """Get database type: sqlite or mysql"""
        return self._config.get("database", {}).get("type", "sqlite")

    @property
    def sqlite_path(self) -> str:
        """Get SQLite database path"""
        return self._config.get("database", {}).get("sqlite_path", "data/hancat.db")

    @property
    def mysql_host(self) -> str:
        """Get MySQL host"""
        return self._config.get("database", {}).get("mysql_host", "localhost")

    @property
    def mysql_port(self) -> int:
        """Get MySQL port"""
        return self._config.get("database", {}).get("mysql_port", 3306)

    @property
    def mysql_user(self) -> str:
        """Get MySQL user"""
        return self._config.get("database", {}).get("mysql_user", "root")

    @property
    def mysql_password(self) -> str:
        """Get MySQL password"""
        return self._config.get("database", {}).get("mysql_password", "")

    @property
    def mysql_database(self) -> str:
        """Get MySQL database name"""
        return self._config.get("database", {}).get("mysql_database", "sora2api")

    @property
    def mysql_pool_size(self) -> int:
        """Get MySQL connection pool size"""
        return self._config.get("database", {}).get("mysql_pool_size", 50)

    # ==================== Redis Configuration ====================
    
    @property
    def redis_enabled(self) -> bool:
        """Get Redis enabled status"""
        return self._config.get("redis", {}).get("enabled", False)

    @property
    def redis_host(self) -> str:
        """Get Redis host"""
        return self._config.get("redis", {}).get("host", "localhost")

    @property
    def redis_port(self) -> int:
        """Get Redis port"""
        return self._config.get("redis", {}).get("port", 6379)

    @property
    def redis_password(self) -> str:
        """Get Redis password"""
        return self._config.get("redis", {}).get("password", "")

    @property
    def redis_db(self) -> int:
        """Get Redis database number"""
        return self._config.get("redis", {}).get("db", 0)

    @property
    def redis_lock_timeout(self) -> int:
        """Get Redis lock timeout in seconds"""
        return self._config.get("redis", {}).get("lock_timeout", 300)

    # ==================== Lambda Configuration ====================

    @property
    def lambda_max_concurrency(self) -> int:
        """Get max concurrent Lambda requests"""
        return self._config.get("lambda", {}).get("max_concurrency", 5)

    @property
    def lambda_max_connections(self) -> int:
        """Get Lambda HTTP client max connections"""
        return self._config.get("lambda", {}).get("max_connections", 20)

    @property
    def lambda_max_keepalive_connections(self) -> int:
        """Get Lambda HTTP client max keepalive connections"""
        return self._config.get("lambda", {}).get("max_keepalive_connections", 10)

    @property
    def lambda_keepalive_expiry(self) -> float:
        """Get Lambda HTTP client keepalive expiry in seconds"""
        return self._config.get("lambda", {}).get("keepalive_expiry", 20.0)

    @property
    def lambda_timeout(self) -> float:
        """Get Lambda HTTP client timeout in seconds"""
        return self._config.get("lambda", {}).get("timeout", 30.0)

    # ==================== Translation Configuration ====================

    @property
    def translation_enabled(self) -> bool:
        """Get translation enabled status"""
        return self._config.get("translation", {}).get("enabled", False)

    def set_translation_enabled(self, enabled: bool):
        """Set translation enabled/disabled"""
        if "translation" not in self._config:
            self._config["translation"] = {}
        self._config["translation"]["enabled"] = enabled

    @property
    def translation_api_url(self) -> str:
        """Get translation API URL"""
        return self._config.get("translation", {}).get("api_url", "")

    def set_translation_api_url(self, url: str):
        """Set translation API URL"""
        if "translation" not in self._config:
            self._config["translation"] = {}
        self._config["translation"]["api_url"] = url

    @property
    def translation_api_key(self) -> str:
        """Get translation API key"""
        return self._config.get("translation", {}).get("api_key", "")

    def set_translation_api_key(self, key: str):
        """Set translation API key"""
        if "translation" not in self._config:
            self._config["translation"] = {}
        self._config["translation"]["api_key"] = key

    @property
    def translation_model(self) -> str:
        """Get translation model name"""
        return self._config.get("translation", {}).get("model", "gpt-4o-mini")

    def set_translation_model(self, model: str):
        """Set translation model name"""
        if "translation" not in self._config:
            self._config["translation"] = {}
        self._config["translation"]["model"] = model

    @property
    def translation_timeout(self) -> int:
        """Get translation timeout in seconds"""
        return self._config.get("translation", {}).get("timeout", 30)

    # Legacy aliases for backward compatibility
    @property
    def cloudflare_solver_enabled(self) -> bool:
        """Legacy alias for cf_enabled"""
        return self.cf_enabled

    @property
    def cloudflare_solver_api_url(self) -> str:
        """Legacy alias for cf_api_url"""
        return self.cf_api_url

# Global config instance
config = Config()
