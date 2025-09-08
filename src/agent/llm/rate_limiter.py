import time
from typing import Dict, List, Optional
from collections import deque
import threading
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RateLimiter")

class RateLimiter:
    def __init__(
        self,
        provider: str,
        requests_per_minute: int,
        input_tokens_per_minute: int,
        output_tokens_per_minute: int,
        input_token_price_per_million: float,
        output_token_price_per_million: float,
        buffer_percentage: float=0.1 # 缓冲区比例，避免达到限制
    ):
        self.provider = provider
        self.requests_per_minute = requests_per_minute * (1 - buffer_percentage)
        self.input_tokens_per_minute = input_tokens_per_minute * (1 - buffer_percentage)
        self.output_tokens_per_minute = output_tokens_per_minute * (1 - buffer_percentage)

        # 价格
        self.input_token_price_per_million = input_token_price_per_million / 1_000_000
        self.output_token_price = output_token_price_per_million / 1_000_000

        # 记录1分钟之内
        self.request_timestamps = deque()
        self.input_token_usage = deque()
        self.output_token_usage = deque()

        # 总记录
        self.total_requests = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

        self.lock = threading.Lock()

    def _get_usage_count(self, usage_queue: deque):
        return sum(count for _, count in usage_queue)

    def _clean_old_entries(self, usage_queue: deque, current_time: float):
        one_minute_ago = current_time - 60
        
        # (timestamp, value) in usage_queue, value是token消耗量
        # 如果时间超过1分钟之前, 就移除
        if usage_queue and isinstance(usage_queue[0], tuple):
            while usage_queue and usage_queue[0][0] < one_minute_ago:
                usage_queue.popleft()
        else:
            while usage_queue and usage_queue[0] < one_minute_ago:
                usage_queue.popleft()

    def wait_if_needed(self, input_tokens: int, estimated_output_tokens: Optional[int] = None):
        with self.lock:
            if estimated_output_tokens is None:
                estimated_output_tokens = input_tokens // 2

            if input_tokens > self.input_tokens_per_minute or estimated_output_tokens > self.output_tokens_per_minute:
                logger.warning(
                    f"Request uses more tokens ({input_tokens} in / {estimated_output_tokens} out) "
                    f"than the configured per-minute capacity. This request may never succeed."
                )
            
            while True:
                current_time = time.time()

                # 清除一分钟之前的记录
                self._clean_old_entries(self.request_timestamps, current_time)
                self._clean_old_entries(self.input_token_usage, current_time)
                self._clean_old_entries(self.output_token_usage, current_time)

                # 计算一分钟之内的总数
                current_requests = len(self.request_timestamps)
                current_input_tokens = self._get_usage_count(self.input_token_usage)
                current_output_tokens = self._get_usage_count(self.output_token_usage)

                # 如果满足要求继续生成
                if ((current_requests + 1) <= self.requests_per_minute and
                    (current_input_tokens + input_tokens) <= self.input_tokens_per_minute and
                    (current_output_tokens + estimated_output_tokens) <= self.output_tokens_per_minute):
                    break
                
                # 计算等待时间
                wait_time = 0
                if self.request_timestamps:
                    wait_time = max(wait_time, 60 - (current_time - self.request_timestamps[0]))
                if self.input_token_usage:
                    wait_time = max(wait_time, 60 - (current_time - self.input_token_usage[0][0]))
                if self.output_token_usage:
                    wait_time = max(wait_time, 60 - (current_time - self.output_token_usage[0][0]))
                
                # If wait_time is still <= 0, we won't fix usage by waiting
                if wait_time <= 0:
                    logger.warning(
                        "Waiting cannot reduce usage enough to allow this request; "
                        "request exceeds per-minute capacity or usage remains too high."
                    )
                    break

                logger.info(f"Rate limit approaching for {self.provider}. Waiting {wait_time:.2f} seconds...")
                time.sleep(wait_time)

    def record_request(self, input_tokens: int, output_tokens: int):
        with self.lock:
            current_time = time.time()
            
            # 记录请求和token使用量
            self.request_timestamps.append(current_time)
            self.input_token_usage.append((current_time, input_tokens))
            self.output_token_usage.append((current_time, output_tokens))
            
            # 更新总记录
            self.total_requests += 1
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            
            # 计算花费
            input_cost = input_tokens * self.input_token_price
            output_cost = output_tokens * self.output_token_price
            total_cost = input_cost + output_cost
            self.total_cost += total_cost
            
            logger.info(
                f"{self.provider} Request: {self.total_requests} | "
                f"Tokens: {input_tokens}in/{output_tokens}out | "
                f"Cost: ${total_cost:.6f} | "
                f"Total Cost: ${self.total_cost:.6f}"
            )

    def print_usage_stats(self):
        with self.lock:
            logger.info(f"{self.provider} Usage Statistics:")
            logger.info(f"  Total Requests: {self.total_requests}")
            logger.info(f"  Total Input Tokens: {self.total_input_tokens}")
            logger.info(f"  Total Output Tokens: {self.total_output_tokens}")
            logger.info(f"  Total Cost: ${self.total_cost:.6f}")