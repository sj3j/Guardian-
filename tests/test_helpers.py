import unittest
from types import SimpleNamespace
from background import has_link, has_username, has_tag

class DummyMessage:
    def __init__(self, text="", caption="", entities=None, caption_entities=None):
        self.text = text
        self.caption = caption
        self.entities = entities or []
        self.caption_entities = caption_entities or []

class TestHelpers(unittest.TestCase):
    def test_has_link(self):
        self.assertTrue(has_link(DummyMessage("Check out https://telegram.org")))
        self.assertTrue(has_link(DummyMessage("Join t.me/example")))
        self.assertTrue(has_link(DummyMessage(caption="See http://example.com")))
        self.assertFalse(has_link(DummyMessage("Hello world how are you")))

    def test_has_username(self):
        self.assertTrue(has_username(DummyMessage("Follow @mychannel")))
        self.assertTrue(has_username(DummyMessage(caption="DM me at @admin_user")))
        self.assertFalse(has_username(DummyMessage("Normal message without handle")))

    def test_has_tag(self):
        entity = SimpleNamespace(type="MessageEntityType.TEXT_MENTION")
        self.assertTrue(has_tag(DummyMessage("Hello user", entities=[entity])))
        self.assertFalse(has_tag(DummyMessage("Hello user")))

if __name__ == "__main__":
    unittest.main()

