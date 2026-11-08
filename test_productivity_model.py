import unittest

from productivity_model import rate_productivity


class ProductivityModelTests(unittest.TestCase):
    def test_score_is_based_on_daily_goal_and_capped(self):
        self.assertEqual(rate_productivity(60, 120)["score"], 50)
        self.assertEqual(rate_productivity(180, 120)["score"], 100)

    def test_rating_describes_progress(self):
        self.assertEqual(rate_productivity(0, 120)["rating"], "Ready when you are")
        self.assertEqual(rate_productivity(90, 120)["rating"], "Great progress")
        self.assertTrue(rate_productivity(120, 120)["goal_reached"])

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            rate_productivity(-1, 120)
        with self.assertRaises(ValueError):
            rate_productivity(10, 0)


if __name__ == "__main__":
    unittest.main()
