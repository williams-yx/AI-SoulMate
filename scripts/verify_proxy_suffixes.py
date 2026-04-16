import os


def get_config_allowed():
    try:
        # 尝试从 backend.config.Config 读取（会受环境变量影响）
        from backend.config import Config
        allowed_raw = getattr(Config, "STUDIO_PROXY_ALLOWED_SUFFIXES", None)
    except Exception:
        allowed_raw = None
    if not allowed_raw:
        allowed_raw = os.getenv("STUDIO_PROXY_ALLOWED_SUFFIXES", "tencentcos.cn,cos.ap-,myqcloud.com,aliyuncs.com")
    allowed_suffixes = [s.strip().lower() for s in str(allowed_raw or "").split(",") if s.strip()]
    return allowed_suffixes


def is_allowed(host: str, allowed_suffixes) -> bool:
    host = (host or "").lower()
    return any(s in host for s in allowed_suffixes)


if __name__ == '__main__':
    print("ENV STUDIO_PROXY_ALLOWED_SUFFIXES:", os.getenv("STUDIO_PROXY_ALLOWED_SUFFIXES"))
    allowed = get_config_allowed()
    print("Resolved allowed_suffixes:", allowed)
    print()
    test_hosts = [
        "oss-example.tencentcos.cn",
        "mybucket.cos.ap-shanghai.myqcloud.com",
        "assets.aliyuncs.com",
        "files.cloud.tencent.com",
        "cdn.example.com",
        "example.otherdomain.com",
    ]
    for h in test_hosts:
        print(f"{h} -> {'ALLOWED' if is_allowed(h, allowed) else 'BLOCKED'}")
