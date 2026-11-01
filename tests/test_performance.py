import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import time
import database
import background

class TestPerformanceOptimizations(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.test_dir = tempfile.mkdtemp()
        self.db_path = f"{self.test_dir}/test.db"
        database.init_db(self.db_path)
        database._locks_cache.clear()
        background._admin_cache.clear()
        background._clean_text_cache.clear()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir)
        database._locks_cache.clear()

    def test_locks_cache_avoids_disk_reads(self):
        chat_id = -1009999
        # First call populates cache
        locks1 = database.get_chat_locks(chat_id, self.db_path)
        self.assertIn((self.db_path, chat_id), database._locks_cache)

        # Update lock and check cache sync
        database.set_chat_lock(chat_id, "photos", True, self.db_path)
        locks2 = database.get_chat_locks(chat_id, self.db_path)
        self.assertTrue(locks2["photos"])

    def test_admin_cache_avoids_telegram_api_flood(self):
        async def run_test():
            dummy_bot = MagicMock()
            dummy_member = MagicMock()
            dummy_member.privileges = True
            dummy_bot.get_chat_member = AsyncMock(return_value=dummy_member)

            dummy_msg = MagicMock()
            dummy_msg.chat.id = -100123
            dummy_msg.from_user.id = 555
            dummy_msg.sender_chat = None

            # 1st call: calls get_chat_member
            res1 = await background.is_admin(dummy_bot, dummy_msg)
            self.assertTrue(res1)
            self.assertEqual(dummy_bot.get_chat_member.call_count, 1)

            # 2nd call: hits cache, doesn't call get_chat_member again
            res2 = await background.is_admin(dummy_bot, dummy_msg)
            self.assertTrue(res2)
            self.assertEqual(dummy_bot.get_chat_member.call_count, 1)

        import asyncio
        asyncio.run(run_test())

    def test_check_badwords_skips_trivial_messages(self):
        async def run_test():
            dummy_client = MagicMock()
            dummy_msg = MagicMock()

            with patch("background._call_gemini_sync") as mock_gemini:
                # Emojis only -> should return False immediately without calling Gemini
                res1 = await background.check_badwords(dummy_client, dummy_msg, "😂😂🔥")
                self.assertEqual(res1, "False")
                mock_gemini.assert_not_called()

                # Numbers/symbols -> should return False without calling Gemini
                res2 = await background.check_badwords(dummy_client, dummy_msg, "12345???")
                self.assertEqual(res2, "False")
                mock_gemini.assert_not_called()

                # Short text (<3 chars) -> should return False without calling Gemini
                res3 = await background.check_badwords(dummy_client, dummy_msg, "ok")
                self.assertEqual(res3, "False")
                mock_gemini.assert_not_called()

        import asyncio
        asyncio.run(run_test())

    def test_clean_text_cache_prevents_duplicate_ai_calls(self):
        async def run_test():
            dummy_client = MagicMock()
            dummy_msg = MagicMock()

            with patch("background._call_gemini_sync", return_value="False") as mock_gemini:
                # 1st time: calls Gemini
                res1 = await background.check_badwords(dummy_client, dummy_msg, "السلام عليكم ورحمة الله")
                self.assertEqual(res1, "False")
                self.assertEqual(mock_gemini.call_count, 1)

                # 2nd time: returns from cache without calling Gemini
                res2 = await background.check_badwords(dummy_client, dummy_msg, "السلام عليكم ورحمة الله")
                self.assertEqual(res2, "False")
                self.assertEqual(mock_gemini.call_count, 1)

        import asyncio
        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
