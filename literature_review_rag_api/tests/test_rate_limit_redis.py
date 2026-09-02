"""RedisFixedWindowCounter behavior with a duck-typed fake redis client."""


class FakePipe:
    def __init__(self, store):
        self.store = store
        self.ops = []

    def incr(self, k):
        self.ops.append(("incr", k))
        return self

    def expire(self, k, s):
        self.ops.append(("expire", k))
        return self

    def execute(self):
        out = []
        for op, k in self.ops:
            if op == "incr":
                self.store[k] = int(self.store.get(k, 0)) + 1
                out.append(self.store[k])
            else:
                out.append(True)
        return out


class FakeRedis:
    def __init__(self):
        self.store = {}

    def pipeline(self):
        return FakePipe(self.store)

    def get(self, k):
        return self.store.get(k)

    def delete(self, k):
        self.store.pop(k, None)

    def ping(self):
        return True


def test_redis_counter_increments_and_resets():
    from literature_rag.rate_limiter import RedisFixedWindowCounter
    c = RedisFixedWindowCounter(FakeRedis(), window_seconds=60)
    assert c.increment("ip1") == 1
    assert c.increment("ip1") == 2
    assert c.get_count("ip1") == 2
    c.reset("ip1")
    assert c.get_count("ip1") == 0
    assert c.increment("ip2") == 1  # isolation


def test_rate_limiter_uses_memory_without_redis_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    from literature_rag.rate_limiter import RateLimiter, RateLimitConfig, SlidingWindowCounter
    rl = RateLimiter(RateLimitConfig())
    assert isinstance(rl._default_counter, SlidingWindowCounter)
