#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用重试与多源容错工具
—— 复用小旭恐慌指数项目的 resilience 思路，精简为本项目所需。
"""
import time
import functools

def retry(max_tries: int = 3, delay: float = 2.0, backoff: float = 1.5,
          exceptions: tuple = (Exception,)):
    """装饰器：对可能失败的函数做指数退避重试。"""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            d = delay
            last = None
            for i in range(max_tries):
                try:
                    return fn(*a, **kw)
                except exceptions as e:
                    last = e
                    if i < max_tries - 1:
                        time.sleep(d)
                        d *= backoff
            # 全部失败，抛出最后一次异常（调用方可捕获转 fallback）
            raise last
        return wrapper
    return deco

def fallback_chain(*fetchers):
    """
    依次尝试多个取数函数，返回第一个成功（非 None）的结果。
    每个 fetcher 是零参 callable，返回 None 表示失败。
    用法：
        val = fallback_chain(fetch_tencent, fetch_sina, fetch_akshare)
        if val is None:  # 全部失败
            ...
    """
    errors = []
    for f in fetchers:
        try:
            r = f()
            if r is not None:
                return r
        except Exception as e:
            errors.append(f"{getattr(f, '__name__', repr(f))}: {e}")
    return None
