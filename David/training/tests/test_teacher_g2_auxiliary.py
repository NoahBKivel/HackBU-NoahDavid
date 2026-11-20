"""Keep authorized G2 substitutions separate from protected main labels."""

import unittest

from intent_training.teacher.dispatch import MODELS, SONNET_MODEL, vote_model


class G2AuxiliaryPolicyTests(unittest.TestCase):
    def batch(self, *, stage="main_completion", questions=None, actual=None, slot="sol"):
        return {"pass": stage, "records": [{"pass": stage,
                "questions": {key: {} for key in (questions if questions is not None else ["G2#R1"])}}],
                "model_overrides": {slot: actual or MODELS["terra"]}}

    def test_authorized_auxiliary_models_keep_actual_identity(self):
        for model in (MODELS["terra"], SONNET_MODEL):
            with self.subTest(model=model):
                self.assertEqual(vote_model(self.batch(actual=model), "sol"), model)

    def test_main_and_mixed_completion_allow_terra_but_not_sonnet(self):
        for stage, questions in (("main", ["G2#R1"]), ("main", ["M1"]),
                                 ("main_completion", ["G2#R1", "M1"]),
                                 ("main_completion", ["G5"]), ("main_completion", [])):
            with self.subTest(stage=stage, questions=questions):
                self.assertEqual(vote_model(self.batch(stage=stage, questions=questions), "sol"), MODELS["terra"])
                with self.assertRaises(ValueError):
                    vote_model(self.batch(stage=stage, questions=questions, actual=SONNET_MODEL), "sol")

    def test_unapproved_model_and_secondary_override_stay_rejected(self):
        with self.assertRaises(ValueError):
            vote_model(self.batch(actual="unapproved-model"), "sol")
        with self.assertRaises(ValueError):
            vote_model(self.batch(actual=SONNET_MODEL, slot="terra"), "terra")

    def test_mixed_record_pass_cannot_be_hidden_by_batch_stage(self):
        batch = self.batch(actual=SONNET_MODEL)
        batch["records"][0]["pass"] = "main"
        with self.assertRaises(ValueError):
            vote_model(batch, "sol")


if __name__ == "__main__":
    unittest.main()
