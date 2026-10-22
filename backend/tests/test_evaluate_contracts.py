"""
test_evaluate_contracts.py
Unit tests for the standalone CUAD contract evaluation script (scripts/evaluate_contracts.py).
"""

import os
import sys

# Ensure backend root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.schemas import ClauseCategory
from scripts.evaluate_contracts import (
    ALL_41_CUAD_CATEGORIES,
    compute_metrics,
    load_cuad_dataset,
    render_evaluation_table,
    run_evaluation,
)


def test_load_cuad_dataset_mock():
    """
    Ensure mock CUAD dataset loads properly with required fields and valid categories.
    """
    dataset = load_cuad_dataset(force_mock=True)
    assert len(dataset) >= 5

    for contract in dataset:
        assert "title" in contract
        assert len(contract["title"]) > 0
        assert "text" in contract
        assert len(contract["text"]) > 100
        assert "ground_truth_categories" in contract
        assert isinstance(contract["ground_truth_categories"], set)

        # Ensure all ground-truth categories belong to the 41 CUAD categories
        for cat in contract["ground_truth_categories"]:
            assert cat in ALL_41_CUAD_CATEGORIES


def test_compute_metrics_accuracy_and_edge_cases():
    """
    Verify precision, recall, and F1 calculations including perfect and zero cases.
    """
    eval_results = [
        {
            "contract": "Contract 1",
            "ground_truth": {"Governing Law", "Cap On Liability", "Audit Rights"},
            "predicted": {"Governing Law", "Cap On Liability", "Non-Compete"},
        },
        {
            "contract": "Contract 2",
            "ground_truth": {"Governing Law", "Termination For Convenience"},
            "predicted": {"Governing Law", "Termination For Convenience"},
        },
    ]

    metrics = compute_metrics(eval_results)
    assert len(metrics) == 41

    # 1. Governing Law: in GT (2), in Pred (2), TP=2, FP=0, FN=0 -> Precision=1.0, Recall=1.0, F1=1.0
    gov_law = metrics[ClauseCategory.GOVERNING_LAW.value]
    assert gov_law["true_positives"] == 2
    assert gov_law["false_positives"] == 0
    assert gov_law["false_negatives"] == 0
    assert gov_law["precision"] == 1.0
    assert gov_law["recall"] == 1.0
    assert gov_law["f1_score"] == 1.0
    assert gov_law["tier"] == "STRONG (High F1)"

    # 2. Audit Rights: in GT (1), in Pred (0), TP=0, FP=0, FN=1 -> Precision=0.0, Recall=0.0, F1=0.0
    audit = metrics[ClauseCategory.AUDIT_RIGHTS.value]
    assert audit["true_positives"] == 0
    assert audit["false_negatives"] == 1
    assert audit["precision"] == 0.0
    assert audit["recall"] == 0.0
    assert audit["f1_score"] == 0.0
    assert audit["tier"] == "LOW (Missed)"

    # 3. Non-Compete: in GT (0), in Pred (1), TP=0, FP=1, FN=0 -> Precision=0.0, Recall=0.0, F1=0.0
    non_compete = metrics[ClauseCategory.NON_COMPETE.value]
    assert non_compete["true_positives"] == 0
    assert non_compete["false_positives"] == 1
    assert non_compete["precision"] == 0.0
    assert non_compete["f1_score"] == 0.0

    # 4. Absent and unpredicted category: Double Cap (GT=0, Pred=0) -> Precision=1.0, Recall=1.0, F1=1.0
    double_cap = metrics[ClauseCategory.DOUBLE_CAP.value]
    assert double_cap["ground_truth_count"] == 0
    assert double_cap["predicted_count"] == 0
    assert double_cap["precision"] == 1.0
    assert double_cap["recall"] == 1.0
    assert double_cap["f1_score"] == 1.0


def test_render_evaluation_table_output():
    """
    Ensure render_evaluation_table formats clean ASCII table with required headers and statistics.
    """
    eval_results = [
        {
            "contract": "Contract A",
            "ground_truth": {"Governing Law", "Cap On Liability"},
            "predicted": {"Governing Law"},
        }
    ]
    metrics = compute_metrics(eval_results)
    table_str = render_evaluation_table(metrics)

    assert "CUAD 41-CLAUSE BENCHMARK ACCURACY EVALUATION REPORT" in table_str
    assert "Category" in table_str
    assert "Precision" in table_str
    assert "Recall" in table_str
    assert "F1-Score" in table_str
    assert "Performance Tier" in table_str
    assert "SUMMARY INSIGHTS:" in table_str
    assert "OVERALL MACRO METRICS:" in table_str


def test_run_evaluation_in_process_execution(tmp_path):
    """
    Test running the full evaluation in-process on 2 contracts, including JSON output export.
    """
    json_path = str(tmp_path / "test_eval_metrics.json")
    metrics, table_str = run_evaluation(
        num_contracts=2,
        force_mock=True,
        seed=123,
        output_json=json_path,
    )

    assert len(metrics) == 41
    assert "CUAD 41-CLAUSE BENCHMARK ACCURACY EVALUATION REPORT" in table_str
    assert os.path.exists(json_path)

    # Verify JSON content
    import json
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["num_evaluated_contracts"] == 2
    assert "metrics" in data
    assert len(data["metrics"]) == 41
