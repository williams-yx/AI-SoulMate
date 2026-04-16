"""
用户相关的数据模型
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class User(BaseModel):
    """用户模型"""
    id: Optional[str] = None
    username: str
    email: Optional[EmailStr] = None
    password_hash: Optional[str] = None
    credits: int = 100
    created_at: Optional[datetime] = None
    is_active: bool = True
    avatar: Optional[str] = None
    role: Optional[str] = "student"  # student/teacher/admin
    phone: Optional[str] = None
    openid: Optional[str] = None  # 微信 openid


class UserCreate(BaseModel):
    """用户创建模型"""
    username: str
    password: str
    password_confirm: str  # 确认密码
    register_via: Optional[str] = "account"  # account | phone | email
    # 可选绑定项
    phone: Optional[str] = None
    phone_code: Optional[str] = None  # 手机验证码
    email: Optional[EmailStr] = None
    email_code: Optional[str] = None  # 邮箱验证码
    wechat_code: Optional[str] = None  # 微信授权码
    github_code: Optional[str] = None  # GitHub授权码


class UserLogin(BaseModel):
    """用户登录模型"""
    # 方式1: 用户名+密码，需先调 login/account-request 拿 one_time_token
    username: Optional[str] = None
    password: Optional[str] = None
    login_code: Optional[str] = None  # 兼容旧版：图形验证码
    captcha_id: Optional[str] = None  # 兼容旧版
    one_time_token: Optional[str] = None  # 发码/account-request 返回，提交验证时必带；验证失败时接口返回新 token

    # 方式2: 手机号+验证码，需先 send-code 拿 one_time_token
    phone: Optional[str] = None
    phone_code: Optional[str] = None

    # 方式3: 邮箱+验证码，需先 send-email-code 拿 one_time_token
    email: Optional[EmailStr] = None
    email_code: Optional[str] = None

    # 方式4: 微信授权
    wechat_code: Optional[str] = None

    # 方式5: GitHub授权
    github_code: Optional[str] = None


class AdminLogin(BaseModel):
    """管理员登录模型"""
    username: str
    password: str


# 导出
__all__ = ["User", "UserCreate", "UserLogin", "AdminLogin"]
