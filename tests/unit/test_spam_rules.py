from datetime import datetime, time, timezone

import pytest

from tests.conftest import use_service

with use_service("spam-filter"):
    from app.blacklist import matches_known_spam_prefix
    from app.rules import (
        rule_no_caller_id,
        rule_outside_business_hours,
        rule_repeat_calls,
    )


class TestMatchesKnownSpamPrefix:
    def test_matches_generic_voip_prefix(self):
        assert matches_known_spam_prefix("+56921234567") is True

    def test_matches_800_prefix(self):
        assert matches_known_spam_prefix("+568001234567") is True

    def test_legitimate_mobile_number_does_not_match(self):
        assert matches_known_spam_prefix("+56912345678") is False


class TestRuleOutsideBusinessHours:
    def test_within_business_hours_scores_zero(self):
        call_time = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
        assert rule_outside_business_hours(call_time) == 0.0

    def test_outside_business_hours_scores_positive(self):
        call_time = datetime(2026, 7, 24, 3, 0, tzinfo=timezone.utc)
        assert rule_outside_business_hours(call_time) > 0.0


class TestRuleRepeatCalls:
    def test_below_threshold_scores_zero(self):
        assert rule_repeat_calls(1) == 0.0

    def test_at_threshold_minus_one_scores_partial(self):
        assert rule_repeat_calls(2) == 0.3

    def test_at_or_above_threshold_scores_high(self):
        assert rule_repeat_calls(3) == 0.6
        assert rule_repeat_calls(10) == 0.6


class TestRuleNoCallerId:
    def test_no_caller_id_scores_positive(self):
        assert rule_no_caller_id(False) == 0.4

    def test_with_caller_id_scores_zero(self):
        assert rule_no_caller_id(True) == 0.0
