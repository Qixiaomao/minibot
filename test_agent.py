"""test_agent — 测试 Agent 的核心逻辑"""

import unittest
from unittest.mock import patch, MagicMock
import requests

from agent import Agent


def fake_response(data, status_code=200):
    """构造一个假的 requests.Response"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(f"{status_code}")
    return resp


class TestRequestWithRetry(unittest.TestCase):
    """测试 _request_with_retry 的重试机制"""

    def setUp(self):
        self.agent = Agent(api_key="test-key", base_url="https://fake.api/v1")

    @patch("agent.requests.post")
    def test_success_on_first_try(self, mock_post):
        """第 1 次就成功，不重试"""
        mock_post.return_value = fake_response({"choices": [{"message": {"content": "hi"}}]})

        result = self.agent._request_with_retry({"model": "test", "messages": []})

        self.assertEqual(result["choices"][0]["message"]["content"], "hi")
        self.assertEqual(mock_post.call_count, 1)  # 只调了一次

    @patch("agent.time.sleep")  # mock sleep 避免真的等待
    @patch("agent.requests.post")
    def test_success_after_retry(self, mock_post, mock_sleep):
        """第 1 次失败，第 2 次成功"""
        mock_post.side_effect = [
            requests.exceptions.ConnectionError("网络断了"),
            fake_response({"choices": [{"message": {"content": "ok"}}]}),
        ]

        result = self.agent._request_with_retry({"model": "test", "messages": []})

        self.assertEqual(result["choices"][0]["message"]["content"], "ok")
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once_with(1)  # 第 1 次等 1 秒

    @patch("agent.time.sleep")
    @patch("agent.requests.post")
    def test_retry_exhausted_raises(self, mock_post, mock_sleep):
        """3 次全失败，抛异常"""
        mock_post.side_effect = requests.exceptions.ConnectionError("一直断")

        with self.assertRaises(requests.exceptions.ConnectionError):
            self.agent._request_with_retry({"model": "test", "messages": []})

        self.assertEqual(mock_post.call_count, 3)
        # 验证指数退避：1s → 2s
        calls = [c[0][0] for c in mock_sleep.call_args_list]
        self.assertEqual(calls, [1, 2])

    @patch("agent.time.sleep")
    @patch("agent.requests.post")
    def test_retry_on_429(self, mock_post, mock_sleep):
        """HTTP 429 限流时重试"""
        mock_post.side_effect = [
            fake_response({"error": "rate limited"}, status_code=429),
            fake_response({"choices": [{"message": {"content": "ok"}}]}),
        ]

        result = self.agent._request_with_retry({"model": "test", "messages": []})

        self.assertEqual(result["choices"][0]["message"]["content"], "ok")
        self.assertEqual(mock_post.call_count, 2)

    @patch("agent.requests.post")
    def test_timeout_param(self, mock_post):
        """验证请求带了 timeout 参数"""
        mock_post.return_value = fake_response({"choices": [{"message": {"content": "ok"}}]})

        self.agent._request_with_retry({"model": "test", "messages": []})

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["timeout"], 30)


class TestChat(unittest.TestCase):
    """测试 chat() 的完整流程"""

    def setUp(self):
        self.agent = Agent(api_key="test-key", base_url="https://fake.api/v1")

    @patch("agent.requests.post")
    def test_simple_reply(self, mock_post):
        """普通对话：LLM 直接返回文本"""
        mock_post.return_value = fake_response({
            "choices": [{"message": {"content": "你好！"}, "finish_reason": "stop"}]
        })

        reply = self.agent.chat([{"role": "user", "content": "你好"}])

        self.assertEqual(reply, "你好！")

    @patch("agent.requests.post")
    def test_tool_calling_loop(self, mock_post):
        """工具调用：LLM 先调工具，再返回最终文本"""
        # 第 1 次：LLM 要求调 get_time 工具
        # 第 2 次：LLM 根据工具结果回复
        mock_post.side_effect = [
            fake_response({
                "choices": [{
                    "message": {
                        "content": None,
                        "tool_calls": [{
                            "id": "call_1",
                            "function": {
                                "name": "get_time",
                                "arguments": "{}"
                            }
                        }]
                    },
                    "finish_reason": "tool_calls"
                }]
            }),
            fake_response({
                "choices": [{
                    "message": {"content": "现在是 2026-06-03"},
                    "finish_reason": "stop"
                }]
            }),
        ]

        # 注册一个假工具
        def get_time():
            return "2026-06-03 12:00:00"

        self.agent.tools = MagicMock()
        self.agent.tools.get_schemas.return_value = []
        self.agent.tools.execute.return_value = "2026-06-03 12:00:00"

        reply = self.agent.chat([{"role": "user", "content": "几点了"}])

        self.assertEqual(reply, "现在是 2026-06-03")
        self.assertEqual(mock_post.call_count, 2)
        self.agent.tools.execute.assert_called_once_with("get_time", "{}")

    @patch("agent.requests.post")
    def test_max_rounds_exceeded(self, mock_post):
        """工具调用超过 5 轮，返回超限错误"""
        tool_call_response = fake_response({
            "choices": [{
                "message": {
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {"name": "fake_tool", "arguments": "{}"}
                    }]
                },
                "finish_reason": "tool_calls"
            }]
        })
        mock_post.return_value = tool_call_response

        self.agent.tools = MagicMock()
        self.agent.tools.get_schemas.return_value = []
        self.agent.tools.execute.return_value = "done"

        reply = self.agent.chat([{"role": "user", "content": "循环测试"}])

        self.assertIn("轮次超限", reply)
        self.assertEqual(mock_post.call_count, 5)


if __name__ == "__main__":
    unittest.main()
