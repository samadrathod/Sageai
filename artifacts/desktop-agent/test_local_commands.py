"""
test_local_commands.py — Offline test runner for the Local Command Engine.
"""

from __future__ import annotations
import os
import sys
import unittest

# Ensure the agent directory is on the sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from local_commands.intent_matcher import match_intent
from local_commands.confirmation_manager import requires_confirmation
from local_commands.command_registry import get_handler
from local_commands.memory_commands import handle_remember, handle_recall, handle_forget, handle_forget_all, DB_PATH


class TestLocalCommands(unittest.TestCase):
    
    def test_intent_matching(self):
        # 1. App control
        self.assertEqual(match_intent("Open VS Code").intent, "open_application")
        self.assertEqual(match_intent("Open VS Code").target, "code")
        
        self.assertEqual(match_intent("Close Chrome").intent, "close_application")
        self.assertEqual(match_intent("Close Chrome").target, "chrome.exe")
        
        self.assertEqual(match_intent("Kill Spotify").intent, "kill_process")
        self.assertEqual(match_intent("Kill Spotify").target, "Spotify.exe")

        # 2. File management
        self.assertEqual(match_intent("Create folder called DSA").intent, "create_folder")
        self.assertEqual(match_intent("Create folder called DSA").target, "DSA")
        
        self.assertEqual(match_intent("Create file notes.txt").intent, "create_file")
        self.assertEqual(match_intent("Create file notes.txt").target, "notes.txt")
        
        self.assertEqual(match_intent("Rename notes.txt to final.txt").intent, "rename_file")
        self.assertEqual(match_intent("Rename notes.txt to final.txt").target, "notes.txt")
        self.assertEqual(match_intent("Rename notes.txt to final.txt").extra.get("new_name"), "final.txt")
        
        self.assertEqual(match_intent("Move final.txt to DSA").intent, "move_file")
        self.assertEqual(match_intent("Move final.txt to DSA").target, "final.txt")
        self.assertEqual(match_intent("Move final.txt to DSA").extra.get("destination"), "DSA")
        
        self.assertEqual(match_intent("Delete test.txt").intent, "delete_file")
        self.assertEqual(match_intent("Delete test.txt").target, "test.txt")
        
        self.assertEqual(match_intent("Search files for resume").intent, "search_files")
        self.assertEqual(match_intent("Search files for resume").target, "resume")
        
        self.assertEqual(match_intent("Open Downloads").intent, "open_folder")
        self.assertEqual(match_intent("Open Downloads").target, "~/Downloads")

        # 3. System control
        self.assertEqual(match_intent("Show system info").intent, "system_info")
        
        self.assertEqual(match_intent("Increase volume").intent, "volume_control")
        self.assertEqual(match_intent("Increase volume").target, "up")
        
        self.assertEqual(match_intent("Decrease volume").intent, "volume_control")
        self.assertEqual(match_intent("Decrease volume").target, "down")
        
        self.assertEqual(match_intent("Mute volume").intent, "volume_control")
        self.assertEqual(match_intent("Mute volume").target, "mute")
        
        self.assertEqual(match_intent("Increase brightness").intent, "brightness_control")
        self.assertEqual(match_intent("Increase brightness").target, "up")
        
        self.assertEqual(match_intent("Set brightness to 80%").intent, "brightness_control")
        self.assertEqual(match_intent("Set brightness to 80%").target, "set")
        self.assertEqual(match_intent("Set brightness to 80%").extra.get("level"), 80)
        
        self.assertEqual(match_intent("Turn on Wi-Fi").intent, "wifi_toggle")
        self.assertEqual(match_intent("Turn on Wi-Fi").target, "on")
        
        self.assertEqual(match_intent("Toggle Bluetooth").intent, "bluetooth_toggle")
        self.assertEqual(match_intent("Toggle Bluetooth").target, "toggle")
        
        self.assertEqual(match_intent("Shutdown computer").intent, "shutdown")
        self.assertEqual(match_intent("Restart computer").intent, "restart")
        self.assertEqual(match_intent("Sleep").intent, "sleep")

        # 4. Automation routines
        self.assertEqual(match_intent("Open my coding setup").intent, "coding_setup")
        self.assertEqual(match_intent("Study Mode").intent, "study_mode")
        self.assertEqual(match_intent("Gaming Mode").intent, "gaming_mode")

        # 5. Memory commands
        self.assertEqual(match_intent("Remember my favorite editor is VS Code").intent, "remember")
        self.assertEqual(match_intent("Remember my favorite editor is VS Code").target, "favorite editor")
        self.assertEqual(match_intent("Remember my favorite editor is VS Code").extra.get("value"), "VS Code")
        
        self.assertEqual(match_intent("What is my favorite editor?").intent, "recall")
        self.assertEqual(match_intent("What is my favorite editor?").target, "favorite editor")
        
        self.assertEqual(match_intent("Forget my old phone number").intent, "forget")
        self.assertEqual(match_intent("Forget my old phone number").target, "old phone number")
        
        self.assertEqual(match_intent("Forget everything").intent, "forget_all")

        # 6. Fallback checks (No local command matches)
        self.assertIsNone(match_intent("Explain React Hooks."))
        self.assertIsNone(match_intent("What is quantum computing?"))
        self.assertIsNone(match_intent("Why is my code failing?"))

    def test_confirmation_rules(self):
        self.assertTrue(requires_confirmation("delete_file"))
        self.assertTrue(requires_confirmation("rename_file"))
        self.assertTrue(requires_confirmation("kill_process"))
        self.assertTrue(requires_confirmation("shutdown"))
        self.assertTrue(requires_confirmation("restart"))
        self.assertTrue(requires_confirmation("sleep"))
        
        self.assertFalse(requires_confirmation("open_application"))
        self.assertFalse(requires_confirmation("create_folder"))
        self.assertFalse(requires_confirmation("system_info"))
        self.assertFalse(requires_confirmation("remember"))

    def test_registry_handlers(self):
        self.assertIsNotNone(get_handler("open_application"))
        self.assertIsNotNone(get_handler("close_application"))
        self.assertIsNotNone(get_handler("create_folder"))
        self.assertIsNotNone(get_handler("system_info"))
        self.assertIsNotNone(get_handler("coding_setup"))
        self.assertIsNotNone(get_handler("remember"))
        self.assertIsNone(get_handler("invalid_intent_xyz"))

    def test_memory_operations(self):
        # Clear everything
        handle_forget_all(None, {})
        
        # Test remember
        res = handle_remember("favorite editor", {"value": "VS Code"})
        self.assertIn("remembered", res.lower())
        
        # Test recall (exact)
        res_recall = handle_recall("favorite editor", {})
        self.assertIn("favorite editor is vs code", res_recall.lower())
        
        # Test recall (partial / case-insensitive query)
        res_recall_part = handle_recall("Editor", {})
        self.assertIn("favorite editor is vs code", res_recall_part.lower())
        
        # Test forget
        res_forget = handle_forget("favorite editor", {})
        self.assertIn("forgotten", res_forget.lower())
        
        # Recall again (should not exist)
        res_recall_empty = handle_recall("favorite editor", {})
        self.assertIn("don't have any record", res_recall_empty.lower())




if __name__ == "__main__":
    unittest.main()
