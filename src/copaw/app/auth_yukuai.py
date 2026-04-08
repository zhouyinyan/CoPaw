# -*- coding: utf-8 -*-
"""渝快政扫码登录认证模块。

工作流程：
1. 用户访问 /auth/yukuai/login -> 重定向到渝快政扫码页面
2. 用户扫码后回调到 /auth/yukuai/callback?code=xxx
3. 使用 appkey + appsecret 获取 accessToken
4. 使用 accessToken + code 获取用户信息
5. 使用 accountId 作为唯一标识，创建或登录用户
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from ..constant import SECRET_DIR
from .auth import create_token
from .user_agent_manager import (
    ensure_user_has_default_agent,
    get_user_agents,
    get_user_default_agent,
)

logger = logging.getLogger(__name__)

YUKUAIZHENG_API_BASE = "https://zd-openplatform.bigdatacq.com"
YUKUAIZHENG_QR_LOGIN_URL = "https://zd-login.bigdatacq.com/qrlogin/webAppLogin.htm"

AUTH_YUKUAIZHENG_FILE = SECRET_DIR / "auth_yukuai.json"

TOKEN_EXPIRY_SECONDS = 7 * 24 * 3600


def _chmod_best_effort(path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def _prepare_secret_parent(path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _chmod_best_effort(path.parent, 0o700)


def _load_yukuai_auth_data() -> dict:
    """加载渝快政认证数据."""
    if AUTH_YUKUAIZHENG_FILE.is_file():
        try:
            with open(AUTH_YUKUAIZHENG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load yukuai auth file: %s", exc)
            return {"_auth_load_error": True}
    return {}


def _save_yukuai_auth_data(data: dict) -> None:
    """保存渝快政认证数据."""
    _prepare_secret_parent(AUTH_YUKUAIZHENG_FILE)
    with open(AUTH_YUKUAIZHENG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    _chmod_best_effort(AUTH_YUKUAIZHENG_FILE, 0o600)


def is_yukuai_auth_enabled() -> bool:
    """检查是否启用了渝快政认证."""
    app_key = os.environ.get("COPAW_YUKUAIZHENG_APP_KEY", "").strip()
    app_secret = os.environ.get("COPAW_YUKUAIZHENG_APP_SECRET", "").strip()
    return bool(app_key and app_secret)


def get_yukuai_config() -> Dict[str, str]:
    """获取渝快政配置."""
    return {
        "app_name": os.environ.get("COPAW_YUKUAIZHENG_APP_NAME", "").strip(),
        "protocol_key": os.environ.get("COPAW_YUKUAIZHENG_PROTOCOL_KEY", "").strip(),
        "app_key": os.environ.get("COPAW_YUKUAIZHENG_APP_KEY", "").strip(),
        "app_secret": os.environ.get("COPAW_YUKUAIZHENG_APP_SECRET", "").strip(),
    }


def get_yukuai_login_url(back_url: str) -> str:
    """生成渝快政扫码登录URL."""
    config = get_yukuai_config()
    params = {
        "APP_NAME": config["app_name"],
        "protocolKey": config["protocol_key"],
        "protocol": "oauth2",
        "BACK_URL": back_url,
        "scope": "get_user_info",
        "state": secrets.token_hex(8),
    }
    query_string = "&".join(f"{k}={v}" for k, v in params.items() if v)
    return f"{YUKUAIZHENG_QR_LOGIN_URL}?{query_string}"


def _compute_signature(
    method: str,
    timestamp: str,
    nonce: str,
    uri: str,
    params: Dict[str, Any],
    app_secret: str,
) -> str:
    """计算HMAC-SHA256签名."""
    sorted_params = sorted(params.items(), key=lambda x: x[0].lower())
    param_string = "&".join(f"{k}={v}" for k, v in sorted_params if v)

    string_to_sign = f"{method}\n{timestamp}\n{nonce}\n{uri}\n{param_string}"

    signature = hmac.new(
        app_secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(signature).decode("utf-8")


def _generate_nonce() -> str:
    """生成Nonce: 13位时间毫秒 + 4位随机数."""
    millis = int(time.time() * 1000)
    random_part = secrets.token_hex(2)
    return f"{millis}{random_part}"


def _generate_timestamp() -> str:
    """生成ISO8601格式时间戳."""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+08:00"


async def get_access_token() -> Optional[str]:
    """获取accessToken."""
    config = get_yukuai_config()
    app_key = config["app_key"]
    app_secret = config["app_secret"]

    if not app_key or not app_secret:
        logger.error("渝快政认证配置不完整")
        return None

    url = f"{YUKUAIZHENG_API_BASE}/gettoken.json"
    method = "POST"

    # params = {"appkey": app_key, "appsecret": app_secret}
    params = {"appkey": app_key}

    timestamp = _generate_timestamp()
    nonce = _generate_nonce()
    uri = "/gettoken.json"

    signature = _compute_signature(method, timestamp, nonce, uri, params, app_secret)

    headers = {
        "X-Hmac-Auth-Timestamp": timestamp,
        "X-Hmac-Auth-Nonce": nonce,
        "X-Hmac-Auth-Version": "1.0",
        "apiKey": app_key,
        "X-Hmac-Auth-Signature": signature,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, data=params, headers=headers)
            res.raise_for_status()
            data = res.json()

            if data.get("success") and data.get("content", {}).get("success"):
                token_data = data["content"]["data"]
                logger.info("获取accessToken成功: %s", data)
                return token_data.get("accessToken")

            logger.error("获取accessToken失败: %s", data)
            return None
    except Exception as e:
        logger.error("调用渝快政API失败: %s", e)
        return None


async def get_user_info(access_token: str, code: str) -> Optional[Dict[str, Any]]:
    """获取用户信息."""
    config = get_yukuai_config()
    app_key = config["app_key"]
    app_secret = config["app_secret"]

    url = f"{YUKUAIZHENG_API_BASE}/rpc/oauth2/getuserinfo_bycode.json"
    method = "POST"

    params = {"access_token": access_token, "code": code}
    logger.info("获取渝快政用户信息参数: access_token, %s, code, %s", access_token, code)

    timestamp = _generate_timestamp()
    nonce = _generate_nonce()
    uri = "/rpc/oauth2/getuserinfo_bycode.json"

    signature = _compute_signature(method, timestamp, nonce, uri, params, app_secret)

    headers = {
        "X-Hmac-Auth-Timestamp": timestamp,
        "X-Hmac-Auth-Nonce": nonce,
        "X-Hmac-Auth-Version": "1.0",
        "apiKey": app_key,
        "X-Hmac-Auth-Signature": signature,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, data=params, headers=headers)
            res.raise_for_status()
            data = res.json()

            logger.info("获取渝快政用户信息结果: %s", data)

            if data.get("success") and data.get("content", {}).get("success"):
                return data["content"]["data"]

            logger.error("获取用户信息失败: %s", data)
            return None
    except Exception as e:
        logger.error("调用渝快政用户信息API失败: %s", e)
        return None


def yukuai_register_or_login(
    account_id: str,
    user_info: Dict[str, Any],
) -> Dict[str, Any]:
    """渝快政用户注册或登录.

    每个 accountId 对应一个独立账号。
    返回包含 token 和用户信息的字典.
    """
    data = _load_yukuai_auth_data()

    is_new_user = False
    if "users" not in data:
        data["users"] = {}

    users = data["users"]

    if account_id in users:
        user = users[account_id]
        user["last_login"] = int(time.time())
        data["users"] = users
        _save_yukuai_auth_data(data)
    else:
        users[account_id] = {
            "account": user_info.get("account", ""),
            "last_name": user_info.get("lastName", ""),
            "nick_name": user_info.get("nickNameCn", ""),
            "realm_name": user_info.get("realmName", ""),
            "employee_code": user_info.get("employeeCode", ""),
            "created_at": int(time.time()),
            "last_login": int(time.time()),
        }
        data["users"] = users
        _save_yukuai_auth_data(data)
        is_new_user = True

    logger.info(
        "渝快政用户%s: accountId=%s, account=%s",
        "注册" if is_new_user else "登录",
        account_id,
        user_info.get("account"),
    )

    ensure_user_has_default_agent(account_id)
    
    available_agents = get_user_agents(account_id)
    default_agent = get_user_default_agent(account_id)

    token = create_token(f"yukuai_{account_id}")
    
    return {
        "token": token,
        "user_id": account_id,
        "available_agents": available_agents,
        "default_agent": default_agent,
    }


async def handle_yukuai_callback(code: str) -> Optional[Dict[str, Any]]:
    """处理渝快政扫码回调.

    返回: {"token": "...", "username": "...", "user_id": "...", "available_agents": [...], "default_agent": "..."} 或 None
    """
    access_token = await get_access_token()
    if not access_token:
        return None

    user_info = await get_user_info(access_token, code)
    if not user_info:
        return None

    account_id = str(user_info.get("accountId"))
    if not account_id:
        logger.error("用户信息中缺少accountId")
        return None

    result = yukuai_register_or_login(account_id, user_info)
    if not result:
        return None

    return {
        "token": result["token"],
        "username": user_info.get("lastName") or user_info.get("account", "未知用户"),
        "user_id": result["user_id"],
        "available_agents": result["available_agents"],
        "default_agent": result["default_agent"],
    }