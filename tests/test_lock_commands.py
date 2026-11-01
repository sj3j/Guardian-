import unittest
import database

class TestLockCommands(unittest.TestCase):
    def test_all_locks_have_aliases(self):
        # Every canonical lock must have at least one alias
        alias_targets = set(database.LOCK_ALIASES.values())
        for lock_key in database.LOCK_COLUMNS.keys():
            self.assertIn(lock_key, alias_targets, f"Lock '{lock_key}' has no aliases configured")

    def test_alias_resolutions(self):
        # Test common Arabic phrases
        test_cases = [
            ("الشات", "chat"),
            ("شات", "chat"),
            ("الصور", "photos"),
            ("صور", "photos"),
            ("الفيديو", "videos"),
            ("المتحركات", "gifs"),
            ("الستكرات", "stickers"),
            ("الملصقات", "stickers"),
            ("الصوت", "voice"),
            ("البصمات", "voice"),
            ("التوجيه", "forward"),
            ("الروابط", "links"),
            ("روابط", "links"),
            ("المعرفات", "usernames"),
            ("التاك", "tags"),
            ("الملفات", "files"),
            ("جهات الاتصال", "contacts"),
            ("الكلايش", "spam"),
            ("البوتات", "bots"),
        ]
        for ar_term, expected_key in test_cases:
            self.assertEqual(database.LOCK_ALIASES.get(ar_term), expected_key, f"Failed for {ar_term}")

if __name__ == "__main__":
    unittest.main()

