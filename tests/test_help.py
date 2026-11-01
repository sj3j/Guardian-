import unittest
from background import HELP_TEXT
from database import LOCK_COLUMNS

class TestHelp(unittest.TestCase):
    def test_help_text_content(self):
        self.assertTrue(len(HELP_TEXT) > 100)
        # Check title, developer and sections
        self.assertIn("دليل أوامر ومميزات بوت غارديان (Guardian)", HELP_TEXT)
        self.assertIn("أوامر حماية وأقفال المجموعة", HELP_TEXT)
        self.assertIn("أوامر الإشراف بالرد", HELP_TEXT)
        self.assertIn("ميزات الذكاء الاصطناعي", HELP_TEXT)
        self.assertIn("@sj3js", HELP_TEXT)
        self.assertIn("/help", HELP_TEXT)
        self.assertIn("مساعدة", HELP_TEXT)
        # Ensure Gemini is NEVER mentioned
        self.assertNotIn("Gemini", HELP_TEXT)
        self.assertNotIn("جيميناي", HELP_TEXT)

    def test_help_contains_moderation_commands(self):
        moderation_cmds = ["كتم", "طرد", "رفع الكتم", "رفع الحظر", "/Arise"]
        for cmd in moderation_cmds:
            self.assertIn(cmd, HELP_TEXT)

    def test_help_contains_ai_triggers(self):
        triggers = ["غارديان", "guardian", "جاردين"]
        for trigger in triggers:
            self.assertIn(trigger, HELP_TEXT)

    def test_help_contains_key_locks(self):
        # Ensure lock column Arabic names appear in help
        for ar_name in LOCK_COLUMNS.values():
            self.assertIn(ar_name, HELP_TEXT)

if __name__ == "__main__":
    unittest.main()
