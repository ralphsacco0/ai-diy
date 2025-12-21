"""
Unit tests for helloworld.py
"""
import pytest
from helloworld import greeting

def test_greeting():
    """Test that greeting function returns expected format"""
    result = greeting()
    assert isinstance(result, str)
    assert len(result) > 0
    assert result.strip()  # Not just whitespace

def test_greeting_content():
    """Test that greeting contains expected content"""
    result = greeting()
    # Should be a meaningful message with at least one word
    words = result.strip().split()
    assert len(words) >= 1  # At least one word
