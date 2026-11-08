"""Candidate discrimination, paired selection and serving calibration."""

from .calibration import calibrated_probabilities, fit_calibration, fit_question, prior_offset
from .metrics import auroc, macro_auroc, probabilities, question_aurocs
from .scoring import load_and_score, score_records, target_rows
from .selection import select_candidate

__all__ = ["auroc", "macro_auroc", "probabilities", "question_aurocs", "select_candidate",
           "calibrated_probabilities", "fit_calibration", "fit_question", "prior_offset",
           "load_and_score", "score_records", "target_rows"]
