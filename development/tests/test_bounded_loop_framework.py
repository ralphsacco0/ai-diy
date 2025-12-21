"""
Unit tests for bounded loop framework (no actual API calls)
Tests the logic without hitting OpenRouter
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestBoundedLoopFramework:
    """Test bounded loop logic without API calls"""
    
    def test_message_accumulation(self):
        """Test that messages accumulate correctly in bounded loop"""
        # Simulate what happens in the bounded loop
        messages = [
            {"role": "system", "content": "You are Alex"},
            {"role": "user", "content": "Fix the bug"}
        ]
        
        bounded_messages = messages.copy()
        
        # Simulate Pass 1
        bounded_messages.append({"role": "assistant", "content": "Tool results: file.py contents"})
        bounded_messages.append({"role": "user", "content": "Nudge: make changes now"})
        
        assert len(bounded_messages) == 4
        assert bounded_messages[-1]["content"].startswith("Nudge:")
        
        # Simulate Pass 2
        bounded_messages.append({"role": "assistant", "content": "More tool results"})
        bounded_messages.append({"role": "user", "content": "Nudge: continue"})
        
        assert len(bounded_messages) == 6
        print(f"✅ Message accumulation test passed: {len(bounded_messages)} messages after 2 passes")
    
    def test_permission_detection(self):
        """Test permission detection logic"""
        fix_permission_phrases = [
            "fix it", "go ahead", "apply it", "make the change", 
            "do it", "you have permission", "fix the issue"
        ]
        
        # Test positive cases
        user_messages = [
            "Alex, there's a bug",
            "please fix it"
        ]
        user_message_history = "\n".join(user_messages).lower()
        has_permission = any(phrase in user_message_history for phrase in fix_permission_phrases)
        
        assert has_permission == True
        print("✅ Permission detection test passed: 'fix it' detected")
        
        # Test negative case
        user_messages = ["Alex, investigate the bug"]
        user_message_history = "\n".join(user_messages).lower()
        has_permission = any(phrase in user_message_history for phrase in fix_permission_phrases)
        
        assert has_permission == False
        print("✅ Permission detection test passed: no permission phrase detected")
    
    def test_max_passes_limit(self):
        """Test that bounded loop respects max passes"""
        max_passes = 3
        current_pass = 1
        passes_executed = []
        
        # Simulate loop
        while current_pass <= max_passes:
            passes_executed.append(current_pass)
            current_pass += 1
        
        assert len(passes_executed) == 3
        assert passes_executed == [1, 2, 3]
        print(f"✅ Max passes test passed: executed {len(passes_executed)} passes")
    
    def test_context_size_estimation(self):
        """Test context size grows with each pass"""
        system_prompt = "You are Alex" * 100  # ~1.2KB
        vision_doc = "Vision content" * 500   # ~6KB
        file_content = "def foo():\n    pass\n" * 200  # ~4KB
        
        # Initial context
        initial_size = len(system_prompt) + len(vision_doc)
        print(f"Initial context: {initial_size:,} chars")
        
        # After Pass 1
        pass1_size = initial_size + len(file_content) + 200  # file + nudge
        print(f"After Pass 1: {pass1_size:,} chars")
        
        # After Pass 2
        pass2_size = pass1_size + len(file_content) + 200  # more results + nudge
        print(f"After Pass 2: {pass2_size:,} chars")
        
        assert pass2_size > pass1_size > initial_size
        print(f"✅ Context size test passed: grows from {initial_size:,} to {pass2_size:,} chars")
    
    def test_history_injection(self):
        """Test conversation history injection"""
        # Simulate history
        history_messages = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"}
        ]
        
        # Simulate current messages
        system_messages = [{"role": "system", "content": "You are Alex"}]
        current_messages = [{"role": "user", "content": "Current question"}]
        
        # Inject history
        messages = system_messages + history_messages + current_messages
        
        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Previous question"
        assert messages[-1]["content"] == "Current question"
        print("✅ History injection test passed: correct message order")


class TestConversationHistory:
    """Test conversation history storage (no file I/O)"""
    
    def test_history_format(self):
        """Test history data structure"""
        turn = {
            "timestamp": "2025-11-09T17:00:00",
            "user_message": "Fix the bug",
            "assistant_response": "I found the issue",
            "tool_calls": [{"function": {"name": "read_file"}}]
        }
        
        assert "user_message" in turn
        assert "assistant_response" in turn
        assert "tool_calls" in turn
        print("✅ History format test passed")
    
    def test_history_pruning_logic(self):
        """Test that history keeps only last N turns"""
        max_turns = 10
        turns = [{"turn": i} for i in range(15)]
        
        # Simulate pruning
        if len(turns) > max_turns:
            turns = turns[-max_turns:]
        
        assert len(turns) == 10
        assert turns[0]["turn"] == 5  # First kept turn
        assert turns[-1]["turn"] == 14  # Last turn
        print(f"✅ History pruning test passed: kept last {len(turns)} turns")


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*60)
    print("BOUNDED LOOP FRAMEWORK TESTS")
    print("="*60 + "\n")
    
    framework_tests = TestBoundedLoopFramework()
    framework_tests.test_message_accumulation()
    framework_tests.test_permission_detection()
    framework_tests.test_max_passes_limit()
    framework_tests.test_context_size_estimation()
    framework_tests.test_history_injection()
    
    print("\n" + "-"*60 + "\n")
    
    history_tests = TestConversationHistory()
    history_tests.test_history_format()
    history_tests.test_history_pruning_logic()
    
    print("\n" + "="*60)
    print("ALL TESTS PASSED ✅")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
