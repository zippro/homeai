from __future__ import annotations

import unittest

from app.render_policy import resolve_credit_cost, should_block_final_without_preview


class RenderPolicyTests(unittest.TestCase):
    def test_resolve_credit_cost_preview(self) -> None:
        self.assertEqual(resolve_credit_cost(1, 2, "preview"), 1)

    def test_resolve_credit_cost_final(self) -> None:
        self.assertEqual(resolve_credit_cost(1, 2, "final"), 2)

    def test_resolve_credit_cost_never_negative(self) -> None:
        self.assertEqual(resolve_credit_cost(-5, -2, "preview"), 0)
        self.assertEqual(resolve_credit_cost(-5, -2, "final"), 0)

    def test_preview_gate_disabled(self) -> None:
        blocked = should_block_final_without_preview(
            preview_before_final_required=False,
            tier="final",
            has_completed_preview=False,
        )
        self.assertFalse(blocked)

    def test_preview_gate_only_for_final(self) -> None:
        blocked = should_block_final_without_preview(
            preview_before_final_required=True,
            tier="preview",
            has_completed_preview=False,
        )
        self.assertFalse(blocked)

    def test_preview_gate_blocks_when_needed(self) -> None:
        blocked = should_block_final_without_preview(
            preview_before_final_required=True,
            tier="final",
            has_completed_preview=False,
        )
        self.assertTrue(blocked)


if __name__ == "__main__":
    unittest.main()
