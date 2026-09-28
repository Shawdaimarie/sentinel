"""Ruleset probe for plan step 5 (#53). Must never merge.

This test fails on purpose, to prove that the main-branch ruleset blocks a pull
request whose required checks fail.
"""


def test_ruleset_blocks_failing_pull_requests() -> None:
    assert False, "Deliberate failure: the ruleset must block this PR from merging."
