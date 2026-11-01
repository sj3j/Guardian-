import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import os
import background

class TestGeminiIntegration(unittest.TestCase):
    def setUp(self):
        self.orig_env = os.environ.copy()
        background.api_key_index = 0
        # Clear existing keys for clean test state
        for k in ["GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]:
            if k in os.environ:
                del os.environ[k]

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)
        background.api_key_index = 0

    def test_get_configured_api_keys_empty(self):
        keys = background.get_configured_api_keys()
        self.assertEqual(keys, [])

    def test_get_configured_api_keys_standard_and_numbered(self):
        os.environ["GEMINI_API_KEY"] = "standard_key"
        os.environ["GEMINI_API_KEY_1"] = "key_1"
        os.environ["GEMINI_API_KEY_2"] = "key_2"
        os.environ["GEMINI_API_KEY_3"] = ""  # Should be ignored

        keys = background.get_configured_api_keys()
        self.assertEqual(keys, ["standard_key", "key_1", "key_2"])

    def test_api_key_rotation(self):
        os.environ["GEMINI_API_KEY_1"] = "key_A"
        os.environ["GEMINI_API_KEY_2"] = "key_B"
        background.api_key_index = 0

        self.assertEqual(background.get_next_api_key(), "key_A")
        self.assertEqual(background.get_next_api_key(), "key_B")
        self.assertEqual(background.get_next_api_key(), "key_A")

    def test_call_gemini_sync_no_keys(self):
        result = background._call_gemini_sync(prompt="test", system_instruction="test")
        self.assertEqual(result, "")

    @patch("background.get_configured_api_keys", return_value=["fake_key_1", "fake_key_2"])
    def test_call_gemini_sync_failover(self, mock_keys):
        background.api_key_index = 0
        mock_response = MagicMock()
        mock_response.text = "Hello from Gemini"

        calls = []
        def client_side_effect(api_key):
            calls.append(api_key)
            inst = MagicMock()
            if api_key == "fake_key_1":
                inst.models.generate_content.side_effect = Exception("429 ResourceExhausted: Quota exceeded")
            else:
                inst.models.generate_content.return_value = mock_response
            return inst

        with patch("background.genai") as mock_genai, patch("background.requests.post") as mock_http:
            mock_genai.Client.side_effect = client_side_effect
            result = background._call_gemini_sync(
                prompt="test",
                system_instruction="instruction"
            )
            self.assertEqual(result, "Hello from Gemini")
            self.assertEqual(calls, ["fake_key_1", "fake_key_2"])

    def test_check_badwords_safe_on_error(self):
        async def run_test():
            dummy_msg = MagicMock()
            dummy_client = MagicMock()
            with patch("background._call_gemini_sync", side_effect=Exception("API connection error")):
                res = await background.check_badwords(dummy_client, dummy_msg, "bad word text")
                self.assertEqual(res, "False")

        asyncio.run(run_test())

    def test_check_badwords_detected(self):
        async def run_test():
            dummy_msg = MagicMock()
            dummy_client = MagicMock()
            with patch("background._call_gemini_sync", return_value="True"):
                res = await background.check_badwords(dummy_client, dummy_msg, "offensive phrase")
                self.assertEqual(res, "True")

        asyncio.run(run_test())

    def test_process_text_fallback_on_error(self):
        async def run_test():
            dummy_msg = MagicMock()
            dummy_msg.reply = AsyncMock()
            dummy_client = MagicMock()

            # Test that process_text doesn't raise exception when API fails
            with patch("background._call_gemini_sync", return_value=""):
                await background.process_text(dummy_client, dummy_msg, "غارديان مرحبا")
                dummy_msg.reply.assert_called_once_with("أهلاً بك! أنا غارديان (Guardian) في خدمتك 🤍")

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
