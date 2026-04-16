"""
内容审核服务
包含敏感词过滤、XSS 防护等功能
"""

import re
from typing import Tuple, Optional, List
from logger import logger

try:
    import bleach
    HAS_BLEACH = True
except ImportError:
    HAS_BLEACH = False


class ContentFilter:
    """内容过滤器"""

    # 敏感词列表（示例，生产环境应从文件或数据库加载）
    SENSITIVE_WORDS = [
        "暴力", "色情", "政治", "违法", "诈骗"
    ]

    # 评论图片 URL 白名单：只允许 /uploads/ 开头的相对路径
    _SAFE_IMAGE_PREFIX = "/uploads/"
    # 评论视频 URL 白名单：只允许 /uploads/ 开头的相对路径
    _SAFE_VIDEO_PREFIX = "/uploads/"

    @staticmethod
    def sanitize_for_display(text: str) -> str:
        """
        对用户输入做 XSS 清洗，供安全展示用。
        使用 bleach  stripped 所有 HTML 标签，仅保留纯文本；无 bleach 时退化为正则清洗。
        """
        if not text:
            return ""
        if HAS_BLEACH:
            # 不保留任何 HTML 标签，仅保留纯文本
            return bleach.clean(text, tags=[], strip=True).strip()
        # 退化：基础正则清洗
        script = re.compile(r"<script\b[^>]*>[\s\S]*?</script>", re.IGNORECASE)
        on_evt = re.compile(r"\s+on\w+\s*=\s*[\"'][^\"']*[\"']", re.IGNORECASE)
        on_evt2 = re.compile(r"\s+on\w+\s*=\s*[^\s>]+", re.IGNORECASE)
        js_proto = re.compile(r"javascript\s*:", re.IGNORECASE)
        data_html = re.compile(r"data\s*:\s*text/html[\s,;]", re.IGNORECASE)
        s = script.sub("", text)
        s = on_evt.sub("", s)
        s = on_evt2.sub("", s)
        s = js_proto.sub("", s)
        s = data_html.sub("", s)
        return s.strip()

    @staticmethod
    def filter_image_urls(urls: Optional[List[str]]) -> List[str]:
        """
        过滤评论图片 URL，仅保留白名单内的路径。
        只允许以 /uploads/ 开头的相对路径，拒绝 javascript:、data:、外链等。
        """
        if not urls:
            return []
        safe = []
        for u in urls:
            if not u or not isinstance(u, str):
                continue
            s = u.strip()
            lower = s.lower()
            if lower.startswith("javascript:") or lower.startswith("data:"):
                continue
            if s.startswith(ContentFilter._SAFE_IMAGE_PREFIX):
                safe.append(s)
            elif s.startswith("http://") or s.startswith("https://"):
                continue  # 暂不允许外链，避免追踪/钓鱼
        return safe

    @staticmethod
    def filter_video_urls(urls: Optional[List[str]]) -> List[str]:
        """
        过滤评论视频 URL，仅保留白名单内的路径。
        只允许以 /uploads/ 开头的相对路径，拒绝 javascript:、data:、外链等。
        """
        if not urls:
            return []
        safe = []
        for u in urls:
            if not u or not isinstance(u, str):
                continue
            s = u.strip()
            lower = s.lower()
            if lower.startswith("javascript:") or lower.startswith("data:"):
                continue
            if s.startswith(ContentFilter._SAFE_VIDEO_PREFIX):
                safe.append(s)
            elif s.startswith("http://") or s.startswith("https://"):
                continue  # 暂不允许外链，避免追踪/钓鱼
        return safe

    @staticmethod
    def filter_content(content: str) -> Tuple[bool, Optional[str]]:
        """
        过滤内容（敏感词 + 长度）

        Args:
            content: 要过滤的内容

        Returns:
            (是否通过, 拒绝原因) 元组
        """
        if not content:
            return False, "内容不能为空"

        content_lower = content.lower()

        # 检查敏感词
        for word in ContentFilter.SENSITIVE_WORDS:
            if word in content_lower:
                logger.warning(f"内容包含敏感词: {word}")
                return False, "内容包含敏感词，请修改后重试"

        # 检查内容长度
        if len(content) > 10000:
            return False, "内容过长，请控制在10000字以内"

        return True, None


# 导出
__all__ = ["ContentFilter"]
