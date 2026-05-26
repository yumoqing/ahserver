"""
跨进程缓存同步模块 — Redis Pub/Sub 触发 + 本地进程缓存

每个 Sage 进程维护自己的本地缓存（零延迟读取），
当某个进程执行数据变更后，通过 Redis Pub/Sub 广播失效消息，
所有进程收到后清除对应本地缓存。

使用方式:
    # 1. 在进程初始化时启动
    from ahserver.cache_sync import get_cache_sync
    cache_sync = get_cache_sync()
    await cache_sync.start(redis_url)
    cache_sync.register("llm", callback=reload_llm_data)

    # 2. 在执行 C/U/D 操作后发送失效
    await cache_sync.invalidate("llm")

    # 3. 读取时检查缓存
    if cache_sync.has("llm"):
        return cache_sync.get("llm")
    data = await load_from_db()
    cache_sync.set("llm", data)
"""

import asyncio
import json
import time
import uuid
from appPublic.log import debug, exception


class CacheSync:
    """跨进程缓存同步 — Redis Pub/Sub 触发 + 本地缓存"""

    CHANNEL_PREFIX = "sage:cache:invalidate"

    def __init__(self):
        self._redis = None
        self._pubsub_task = None
        self._running = False
        self._pid = str(uuid.uuid4())[:8]

        # 本地缓存: {table_name: {"data": ..., "version": ..., "ts": ...}}
        self._local_cache = {}

        # 失效回调: {table_name: [callback, ...]}
        self._callbacks = {}

    async def start(self, redis_url: str):
        """启动订阅 — 在进程初始化时调用

        Args:
            redis_url: Redis 连接 URL，如 "redis://127.0.0.1:6379"
        """
        if self._running:
            debug("CacheSync already running")
            return

        import redis.asyncio as aioredis
        self._redis = aioredis.from_url(
            redis_url,
            decode_responses=True,
            socket_keepalive=True,
        )
        self._running = True
        self._pubsub_task = asyncio.create_task(self._listener())
        debug(f"CacheSync started [pid={self._pid}]")

    async def stop(self):
        """停止订阅 — 进程退出时调用"""
        self._running = False
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass
        if self._redis:
            await self._redis.close()
            self._redis = None
        debug(f"CacheSync stopped [pid={self._pid}]")

    async def _listener(self):
        """后台订阅协程 — 持续监听失效消息"""
        pubsub = self._redis.pubsub()
        try:
            await pubsub.subscribe(self.CHANNEL_PREFIX)
            debug(f"CacheSync [pid={self._pid}] subscribed to {self.CHANNEL_PREFIX}")
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        table = data.get("table")
                        version = data.get("version", 0)
                        sender_pid = data.get("pid", "?")
                        if table:
                            await self._on_invalidate(table, version, sender_pid)
                    except Exception as e:
                        exception(f"CacheSync: failed to parse message: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            exception(f"CacheSync listener error: {e}")
        finally:
            try:
                await pubsub.unsubscribe(self.CHANNEL_PREFIX)
                await pubsub.close()
            except Exception:
                pass

    async def _on_invalidate(self, table: str, version: float, sender_pid: str = "?"):
        """收到失效消息后的处理

        只清除比消息版本更新的本地缓存（避免误清旧消息）。
        """
        if table not in self._local_cache:
            return

        cached = self._local_cache[table]
        if version >= cached.get("version", 0):
            debug(f"CacheSync [pid={self._pid}] invalidating table={table} (from pid={sender_pid})")
            self._local_cache.pop(table, None)

            # 调用注册的失效回调
            if table in self._callbacks:
                for cb in self._callbacks[table]:
                    try:
                        if asyncio.iscoroutinefunction(cb):
                            await cb()
                        else:
                            cb()
                    except Exception as e:
                        exception(f"CacheSync callback error for table={table}: {e}")

    async def invalidate(self, table: str, version: float = None):
        """发送失效消息 — 在执行 C/U/D 操作后调用

        同时清除自己的本地缓存并触发回调。
        """
        msg_version = version or time.time()
        msg = json.dumps({
            "table": table,
            "version": msg_version,
            "pid": self._pid,
        })
        try:
            await self._redis.publish(self.CHANNEL_PREFIX, msg)
            debug(f"CacheSync [pid={self._pid}] published invalidate: table={table}")
        except Exception as e:
            exception(f"CacheSync publish error: {e}")

        # 同时清除自己的本地缓存
        await self._on_invalidate(table, msg_version, sender_pid=self._pid)

    def get(self, table: str):
        """获取本地缓存数据"""
        entry = self._local_cache.get(table)
        if entry is None:
            return None
        return entry["data"]

    def set(self, table: str, data, ttl: int = 300):
        """设置本地缓存

        Args:
            table: 缓存标识（通常用表名）
            data: 缓存数据
            ttl: 最大缓存时间（秒），超过此时间自动失效（兜底机制）
        """
        self._local_cache[table] = {
            "data": data,
            "version": time.time(),
            "ts": time.time(),
            "ttl": ttl,
        }

    def has(self, table: str, max_age: int = 300) -> bool:
        """检查缓存是否有效（存在且未过期）

        Args:
            table: 缓存标识
            max_age: 最大允许年龄（秒），超过视为过期

        Returns:
            True 如果缓存有效
        """
        entry = self._local_cache.get(table)
        if entry is None:
            return False
        if time.time() - entry["ts"] > max_age:
            self._local_cache.pop(table, None)
            return False
        return True

    def clear(self, table: str = None):
        """清除指定或全部本地缓存（不发送 Pub/Sub 消息）"""
        if table:
            self._local_cache.pop(table, None)
        else:
            self._local_cache.clear()

    def register(self, table: str, callback):
        """注册失效回调 — 收到失效消息时自动触发

        Args:
            table: 缓存标识
            callback: 回调函数（可以是普通函数或 async 函数）
        """
        if table not in self._callbacks:
            self._callbacks[table] = []
        self._callbacks[table].append(callback)

    def unregister(self, table: str, callback=None):
        """注销失效回调"""
        if table in self._callbacks:
            if callback:
                self._callbacks[table] = [
                    cb for cb in self._callbacks[table] if cb != callback
                ]
            else:
                self._callbacks.pop(table, None)

    @property
    def is_running(self) -> bool:
        return self._running


# 全局单例
_cache_sync_instance = None


def get_cache_sync() -> CacheSync:
    """获取全局 CacheSync 单例"""
    global _cache_sync_instance
    if _cache_sync_instance is None:
        _cache_sync_instance = CacheSync()
    return _cache_sync_instance


def reset_cache_sync():
    """重置单例（主要用于测试）"""
    global _cache_sync_instance
    _cache_sync_instance = None
