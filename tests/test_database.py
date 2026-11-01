import unittest
import os
import shutil
import tempfile
from datetime import datetime, timedelta
import database

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_guardian.db")
        database.init_db(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_default_locks(self):
        locks = database.get_chat_locks(-1001234567, self.db_path)
        self.assertIsInstance(locks, dict)
        self.assertEqual(len(locks), len(database.LOCK_COLUMNS))
        for val in locks.values():
            self.assertFalse(val)

    def test_set_chat_lock(self):
        chat_id = -1001234567
        # Set photos lock to True
        success = database.set_chat_lock(chat_id, "photos", True, self.db_path)
        self.assertTrue(success)
        locks = database.get_chat_locks(chat_id, self.db_path)
        self.assertTrue(locks["photos"])
        self.assertFalse(locks["videos"])

        # Set back to False
        database.set_chat_lock(chat_id, "photos", False, self.db_path)
        locks = database.get_chat_locks(chat_id, self.db_path)
        self.assertFalse(locks["photos"])

    def test_set_all_chat_locks(self):
        chat_id = -1001234567
        # Lock all
        database.set_all_chat_locks(chat_id, True, self.db_path)
        locks = database.get_chat_locks(chat_id, self.db_path)
        for val in locks.values():
            self.assertTrue(val)

        # Unlock all
        database.set_all_chat_locks(chat_id, False, self.db_path)
        locks = database.get_chat_locks(chat_id, self.db_path)
        for val in locks.values():
            self.assertFalse(val)

    def test_muted_and_banned(self):
        chat_id = -1001234567
        user_id = 987654321
        until = datetime.now() + timedelta(hours=1)

        # Save muted
        database.save_muted_member(chat_id, user_id, "TestUser", until, self.db_path)
        muted = database.get_muted_members(chat_id, self.db_path)
        self.assertIn(user_id, muted)
        self.assertEqual(muted[user_id][0], "TestUser")

        # Remove muted
        database.remove_muted_member(chat_id, user_id, self.db_path)
        muted = database.get_muted_members(chat_id, self.db_path)
        self.assertNotIn(user_id, muted)

        # Save banned
        database.save_banned_member(chat_id, user_id, "BannedUser", self.db_path)
        banned = database.get_banned_members(chat_id, self.db_path)
        self.assertIn(user_id, banned)
        self.assertEqual(banned[user_id], "BannedUser")

        # Remove banned
        database.remove_banned_member(chat_id, user_id, self.db_path)
        banned = database.get_banned_members(chat_id, self.db_path)
        self.assertNotIn(user_id, banned)

if __name__ == "__main__":
    unittest.main()

