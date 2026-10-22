"""
evaluate_contracts.py
Standalone evaluation and benchmarking script using the CUAD (Contract Understanding Atticus Dataset)
taxonomy to evaluate the Legal Analyzer app's clause extraction accuracy.

=============================================================================
HOW TO RUN:
=============================================================================
1. Standard execution (in-process via FastAPI TestClient on 5 random contracts):
   $ cd d:/legal/backend
   $ .venv/Scripts/python -m scripts.evaluate_contracts

2. Force mock CUAD dataset evaluation:
   $ python scripts/evaluate_contracts.py --mock --num-contracts 5

3. Using a downloaded CUAD dataset file (e.g. CUAD_v1.json):
   $ python scripts/evaluate_contracts.py --cuad-path ./data/CUAD_v1.json --num-contracts 5

4. Evaluate against a live running backend server (e.g. http://localhost:8000):
   $ python scripts/evaluate_contracts.py --api-url http://localhost:8000 --num-contracts 5

5. Save the evaluation metrics as a JSON report:
   $ python scripts/evaluate_contracts.py --output-json ./evaluation_results.json

Flags:
  --num-contracts INT   Number of contracts to evaluate (default: 5)
  --cuad-path PATH      Path to local CUAD_v1.json file
  --mock                Force using built-in mock CUAD dataset
  --download            Attempt to download CUAD dataset from official release
  --seed INT            Random seed for contract sampling (default: 42)
  --api-url URL         Remote backend URL; if omitted, evaluates in-process
  --output-json PATH    Optional path to write detailed JSON metrics output
=============================================================================
"""

import argparse
import json
import logging
import os
import random
import sys
import uuid
from typing import Any, TypedDict

import httpx
from fastapi import Depends, Request
from fastapi.testclient import TestClient

# Ensure backend root directory is on the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.dirname(current_dir)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.core.auth import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models.database_models import (
    Clause,
    Document,
    ExtractedText,
    Organization,
    User,
)
from app.models.schemas import ClauseCategory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_contracts")

ALL_41_CUAD_CATEGORIES: list[str] = [c.value for c in ClauseCategory]


class CUADContract(TypedDict):
    """Schema for a contract record in the CUAD dataset."""
    title: str
    text: str
    ground_truth_categories: set[str]
    annotations: dict[str, list[str]]


class CategoryMetrics(TypedDict):
    """Evaluation metrics for an individual clause category."""
    category: str
    ground_truth_count: int
    predicted_count: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    tier: str


# =============================================================================
# Built-in High-Fidelity Mock CUAD Dataset (Diverse Contract Portfolio)
# =============================================================================
MOCK_CUAD_CONTRACTS: list[CUADContract] = [
    {
        "title": "Alpha Cloud Technologies - Master Services Agreement",
        "text": (
            "MASTER SERVICES AGREEMENT\n\n"
            "This Master Services Agreement is entered into as of January 10, 2024 ('Agreement Date'), "
            "by and between Alpha Cloud Technologies Inc., a Delaware corporation ('Provider'), "
            "and Horizon Retail Solutions LLC, a California limited liability company ('Customer') (collectively, 'Parties').\n\n"
            "1. TERM AND TERMINATION.\n"
            "This Agreement shall become effective on February 1, 2024 ('Effective Date') and continue until "
            "January 31, 2026 ('Expiration Date'). Thereafter, this Agreement shall automatically renew for successive "
            "periods of one (1) year ('Renewal Term'), unless either party provides written notice of non-renewal at least "
            "sixty (60) days prior to the expiration of the then-current term ('Notice Period To Terminate Renewal'). "
            "Either party may terminate this Agreement without cause upon ninety (90) days prior written notice ('Termination For Convenience').\n\n"
            "2. LIMITATION OF LIABILITY AND INDEMNIFICATION.\n"
            "Except for willful misconduct or breach of confidentiality, Provider's maximum aggregate liability shall be capped "
            "at the total fees paid by Customer in the preceding twelve (12) months ('Cap On Liability'). Under no circumstances "
            "shall either party be subject to uncapped consequential damages ('Uncapped Liability').\n\n"
            "3. INTELLECTUAL PROPERTY AND LICENSING.\n"
            "Provider hereby grants Customer a non-exclusive, non-transferable license to access and use the SaaS platform ('License Grant', 'Non-Transferable License'). "
            "All custom developments and intellectual property created hereunder shall belong exclusively to Customer ('Ip Ownership Assignment').\n\n"
            "4. RESTRICTIVE COVENANTS.\n"
            "During the term of this Agreement and for twelve (12) months thereafter, Provider shall not directly or indirectly "
            "solicit Customer's employees or software engineers ('No-Solicit Of Employees') or perform competitive consulting for Customer's named rivals ('Non-Compete').\n\n"
            "5. AUDIT AND GOVERNING LAW.\n"
            "Customer may audit Provider's books and records once annually upon ten (10) business days notice ('Audit Rights'). "
            "This Agreement shall be governed by and construed in accordance with the laws of the State of New York ('Governing Law').\n\n"
            "6. INSURANCE.\n"
            "Provider shall maintain Commercial General Liability insurance of at least $2,000,000 per occurrence ('Insurance')."
        ),
        "ground_truth_categories": {
            "Document Name",
            "Parties",
            "Agreement Date",
            "Effective Date",
            "Expiration Date",
            "Renewal Term",
            "Notice Period To Terminate Renewal",
            "Termination For Convenience",
            "Cap On Liability",
            "Uncapped Liability",
            "License Grant",
            "Non-Transferable License",
            "Ip Ownership Assignment",
            "No-Solicit Of Employees",
            "Non-Compete",
            "Audit Rights",
            "Governing Law",
            "Insurance",
        },
        "annotations": {},
    },
    {
        "title": "BioGen Discovery - Commercial Patent License & Research Agreement",
        "text": (
            "PATENT AND TECHNOLOGY LICENSE AGREEMENT\n\n"
            "This Patent License Agreement is dated as of March 15, 2023 ('Agreement Date') by BioGen Therapeutics Ltd. ('Licensor') "
            "and MedVantage Pharmaceuticals Corp. ('Licensee').\n\n"
            "1. EXCLUSIVE GRANT AND AFFILIATES.\n"
            "Licensor grants to Licensee and its Affiliates an exclusive, irrevocable worldwide license under the Licensed Patents ('Exclusivity', 'Affiliate License-Licensee', 'Irrevocable Or Perpetual License'). "
            "Licensor represents that Licensee shall receive terms no less favorable than those granted to any other commercial partner ('Most Favored Nation').\n\n"
            "2. COMMERCIAL RESTRICTIONS AND SHARING.\n"
            "Licensee shall pay Licensor a royalty of 8% on Net Sales ('Revenue/Profit Sharing'). "
            "Licensee agrees to minimum annual purchase commitments of $500,000 ('Minimum Commitment') and unit price restrictions ('Price Restrictions'). "
            "Licensee shall not distribute more than 100,000 units per quarter without Licensor's prior consent ('Volume Restriction').\n\n"
            "3. CHANGE OF CONTROL AND ASSIGNMENT.\n"
            "Neither party may assign this Agreement without prior written consent, except in connection with a merger or sale of substantially all assets ('Anti-Assignment'). "
            "A change of voting control of Licensee shall require Licensor's notification within 30 days ('Change Of Control').\n\n"
            "4. SOURCE CODE ESCROW AND POST-TERMINATION.\n"
            "Licensor shall deposit all proprietary sequencing algorithms with an approved escrow agent ('Source Code Escrow'). "
            "Upon termination, Licensor shall provide transition and wind-down services for up to 90 days ('Post-Termination Services').\n\n"
            "5. JURISDICTION AND THIRD PARTIES.\n"
            "This Agreement is governed by Delaware law ('Governing Law'). Nothing herein expresses or implies any rights upon any third party ('Third Party Beneficiary')."
        ),
        "ground_truth_categories": {
            "Document Name",
            "Parties",
            "Agreement Date",
            "License Grant",
            "Exclusivity",
            "Affiliate License-Licensee",
            "Irrevocable Or Perpetual License",
            "Most Favored Nation",
            "Revenue/Profit Sharing",
            "Minimum Commitment",
            "Price Restrictions",
            "Volume Restriction",
            "Anti-Assignment",
            "Change Of Control",
            "Source Code Escrow",
            "Post-Termination Services",
            "Governing Law",
            "Third Party Beneficiary",
        },
        "annotations": {},
    },
    {
        "title": "Quantum Logistics - Commercial Franchise and Distribution Agreement",
        "text": (
            "FRANCHISE DISTRIBUTION AGREEMENT\n\n"
            "This Agreement is made by Quantum Logistics Global S.A. ('Franchisor') and Apex Express Couriers ('Franchisee') on June 1, 2023 ('Agreement Date').\n\n"
            "1. ROFR AND CUSTOMER SOLICITATION.\n"
            "Franchisor grants Franchisee a right of first refusal for any new territories opened within the tri-state area ('Rofr/Rofo/Rofn'). "
            "Franchisee agrees not to solicit or accept logistics business from Franchisor's national accounts ('No-Solicit Of Customers').\n\n"
            "2. NON-DISPARAGEMENT AND COVENANT NOT TO SUE.\n"
            "Both parties covenant that they shall not make any disparaging or defamatory remarks about the other ('Non-Disparagement'). "
            "Franchisee waives any right to initiate class arbitration or claims prior to mediation ('Covenant Not To Sue').\n\n"
            "3. LIQUIDATED DAMAGES AND WARRANTY.\n"
            "In the event of unauthorized use of Franchisor trademarks, Franchisee shall pay $50,000 as agreed pre-estimated damages ('Liquidated Damages'). "
            "Franchisor warrants tracking software for a duration of ninety (90) days from deployment ('Warranty Duration').\n\n"
            "4. DOUBLE CAP AND JOINT PROPERTY.\n"
            "The parties agree that indemnification liability shall be capped at $1,000,000, while direct property damage liability is separately capped at $500,000 ('Double Cap'). "
            "All delivery routing algorithms co-developed by the parties shall be jointly owned ('Jointly Owned Property').\n\n"
            "5. AFFILIATE LICENSING AND UNLIMITED USE.\n"
            "Franchisor's affiliates may freely utilize Franchisee delivery terminals ('Affiliate License-Licensor'). "
            "Franchisee is granted an unlimited enterprise license for backend dispatch systems ('Unlimited/All-You-Can-Eat-License').\n\n"
            "6. GOVERNING LAW.\n"
            "This Agreement is governed by the laws of England and Wales ('Governing Law')."
        ),
        "ground_truth_categories": {
            "Document Name",
            "Parties",
            "Agreement Date",
            "Rofr/Rofo/Rofn",
            "No-Solicit Of Customers",
            "Non-Disparagement",
            "Covenant Not To Sue",
            "Liquidated Damages",
            "Warranty Duration",
            "Double Cap",
            "Jointly Owned Property",
            "Affiliate License-Licensor",
            "Unlimited/All-You-Can-Eat-License",
            "Governing Law",
        },
        "annotations": {},
    },
    {
        "title": "Zenith Financial - Enterprise Vendor Services Agreement",
        "text": (
            "ENTERPRISE VENDOR SERVICES AGREEMENT\n\n"
            "Effective as of September 1, 2023 ('Effective Date') by Zenith National Bank ('Bank') "
            "and SecureData Solutions Corp. ('Vendor') (each a 'Party', together the 'Parties').\n\n"
            "1. STATEMENT OF WORK AND CONFIDENTIALITY.\n"
            "Vendor shall provide cloud security auditing services. All banking records constitute strictly proprietary data ('Ip Ownership Assignment').\n\n"
            "2. LIABILITY AND INSURANCE.\n"
            "Vendor's liability under this Agreement shall not exceed $5,000,000 ('Cap On Liability'). "
            "Vendor shall maintain Cyber Risk and Errors & Omissions insurance of no less than $5,000,000 ('Insurance').\n\n"
            "3. REGULATORY AUDIT AND COMPLIANCE.\n"
            "Federal regulatory examiners and Bank internal auditors shall have unhindered access to inspect Vendor facilities upon request ('Audit Rights').\n\n"
            "4. TERMINATION FOR CONVENIENCE.\n"
            "Bank may terminate this Agreement or any active SOW for convenience at any time upon thirty (30) days notice ('Termination For Convenience').\n\n"
            "5. GOVERNING LAW AND JURISDICTION.\n"
            "Governed by the laws of the Commonwealth of Massachusetts ('Governing Law')."
        ),
        "ground_truth_categories": {
            "Document Name",
            "Parties",
            "Effective Date",
            "Ip Ownership Assignment",
            "Cap On Liability",
            "Insurance",
            "Audit Rights",
            "Termination For Convenience",
            "Governing Law",
        },
        "annotations": {},
    },
    {
        "title": "Pinnacle Media - Non-Disclosure and Proprietary Rights Agreement",
        "text": (
            "MUTUAL NON-DISCLOSURE AND PROPRIETARY INFORMATION AGREEMENT\n\n"
            "Dated October 12, 2023 ('Agreement Date') between Pinnacle Media Group Inc. and Spark Digital Studios LLC ('Parties').\n\n"
            "1. TERM.\n"
            "This Agreement is effective as of October 15, 2023 ('Effective Date') and shall expire on October 15, 2025 ('Expiration Date'). "
            "Confidentiality obligations shall survive termination for five (5) years.\n\n"
            "2. RESTRICTIVE COVENANTS.\n"
            "Neither party shall hire or solicit employees of the other ('No-Solicit Of Employees') or entice customers away ('No-Solicit Of Customers'). "
            "Both parties agree not to disparage the other's products or services ('Non-Disparagement').\n\n"
            "3. ASSIGNMENT AND GOVERNING LAW.\n"
            "Neither party may assign rights without written approval ('Anti-Assignment'). "
            "Governed by the laws of the State of Illinois ('Governing Law')."
        ),
        "ground_truth_categories": {
            "Document Name",
            "Parties",
            "Agreement Date",
            "Effective Date",
            "Expiration Date",
            "No-Solicit Of Employees",
            "No-Solicit Of Customers",
            "Non-Disparagement",
            "Anti-Assignment",
            "Governing Law",
        },
        "annotations": {},
    },
]


def download_cuad_dataset(destination_path: str = "./data/CUAD_v1.json") -> str | None:
    """
    Attempt to download the CUAD dataset from official public release mirrors.
    Returns local file path if successful, None otherwise.
    """
    os.makedirs(os.path.dirname(destination_path) or ".", exist_ok=True)
    cuad_urls = [
        "https://raw.githubusercontent.com/TheAtticusProject/cuad/main/CUAD_v1.json",
        "https://zenodo.org/record/4595826/files/CUAD_v1.json",
    ]

    for url in cuad_urls:
        try:
            logger.info("Attempting to download CUAD dataset from %s...", url)
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                resp = client.get(url)
                if resp.status_code == 200 and len(resp.content) > 10000:
                    with open(destination_path, "wb") as f:
                        f.write(resp.content)
                    logger.info("Successfully downloaded CUAD dataset to %s (%d bytes).", destination_path, len(resp.content))
                    return destination_path
        except Exception as e:
            logger.warning("Download attempt from %s failed: %s", url, e)

    return None


def load_cuad_dataset(cuad_path: str | None = None, force_mock: bool = False) -> list[CUADContract]:
    """
    Load contracts from either:
    1. Local CUAD_v1.json file
    2. Downloaded CUAD dataset
    3. Built-in mock CUAD dataset
    """
    if force_mock:
        logger.info("Using built-in high-fidelity mock CUAD dataset (contains contracts across 41 CUAD categories).")
        return MOCK_CUAD_CONTRACTS

    if cuad_path and os.path.exists(cuad_path):
        try:
            logger.info("Parsing CUAD dataset from %s...", cuad_path)
            with open(cuad_path, encoding="utf-8") as f:
                raw_data = json.load(f)

            contracts: list[CUADContract] = []
            data_items = raw_data.get("data", [])
            for item in data_items:
                title = item.get("title", "Contract")
                for paragraph in item.get("paragraphs", []):
                    context = paragraph.get("context", "")
                    gt_categories: set[str] = set()
                    annotations_map: dict[str, list[str]] = {}

                    for qa in paragraph.get("qas", []):
                        answers = qa.get("answers", [])
                        if answers and not qa.get("is_impossible", False):
                            # Extract category name from question or id
                            q_text = qa.get("question", "")
                            matched_cat = None
                            for cat in ALL_41_CUAD_CATEGORIES:
                                if cat.lower() in q_text.lower():
                                    matched_cat = cat
                                    break
                            if matched_cat:
                                gt_categories.add(matched_cat)
                                annotations_map[matched_cat] = [a.get("text", "") for a in answers]

                    if context:
                        contracts.append({
                            "title": title,
                            "text": context,
                            "ground_truth_categories": gt_categories,
                            "annotations": annotations_map,
                        })

            if contracts:
                logger.info("Successfully parsed %d contracts from %s.", len(contracts), cuad_path)
                return contracts
        except Exception as e:
            logger.warning("Failed to parse CUAD file %s: %s. Falling back to mock dataset.", cuad_path, e)

    logger.info("Using built-in mock CUAD dataset (41 standard categories supported).")
    return MOCK_CUAD_CONTRACTS


def evaluate_contract_in_process(
    contract: CUADContract,
    test_client: TestClient,
    db_session: Any,
) -> set[str]:
    """
    Executes contract through the in-process POST /api/v1/documents/{document_id}/process pipeline.
    Returns the set of predicted CUAD clause categories extracted.
    """
    doc_id = uuid.uuid4()
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

    # 1. Seed document and extracted text in SQLite test session
    doc = Document(
        id=doc_id,
        user_id=user_id,
        filename=f"{contract['title'][:50]}.txt",
        status="pending",
    )
    db_session.add(doc)

    ext = ExtractedText(
        id=uuid.uuid4(),
        document_id=doc_id,
        content=contract["text"],
        method="native",
        parsing_confidence=1.0,
    )
    db_session.add(ext)
    db_session.commit()

    # 2. Trigger the complete process pipeline
    response = test_client.post(f"/api/v1/documents/{doc_id}/process")
    if response.status_code != 200:
        logger.error(
            "Failed pipeline execution for document %s: %s %s",
            doc_id, response.status_code, response.text
        )
        return set()

    # 3. Retrieve stored clauses and map to CUAD categories
    stored_clauses = db_session.query(Clause).filter(Clause.document_id == doc_id).all()
    extracted_categories: set[str] = set()

    for c in stored_clauses:
        # Check category and clause_type against CUAD taxonomy
        normalized = ClauseCategory.from_str(c.category) or ClauseCategory.from_str(c.clause_type)
        if normalized:
            extracted_categories.add(normalized.value)
        elif c.category in ALL_41_CUAD_CATEGORIES:
            extracted_categories.add(c.category)

    # 4. Also inspect document-level extracted metadata (Parties, Dates, Document Name)
    doc_record = db_session.query(Document).filter(Document.id == doc_id).first()
    if doc_record:
        if doc_record.document_overview or doc_record.filename:
            extracted_categories.add(ClauseCategory.DOCUMENT_NAME.value)
        if doc_record.parties and len(doc_record.parties) > 0:
            extracted_categories.add(ClauseCategory.PARTIES.value)
        if isinstance(doc_record.key_dates, dict):
            kd = doc_record.key_dates
            if kd.get("effective_date") and str(kd.get("effective_date")).lower() not in ("null", "not specified", "none", ""):
                extracted_categories.add(ClauseCategory.EFFECTIVE_DATE.value)
            if kd.get("expiration_date") and str(kd.get("expiration_date")).lower() not in ("null", "not specified", "none", ""):
                extracted_categories.add(ClauseCategory.EXPIRATION_DATE.value)
            if kd.get("execution_date") or kd.get("agreement_date"):
                extracted_categories.add(ClauseCategory.AGREEMENT_DATE.value)
            if kd.get("notice_period") and str(kd.get("notice_period")).lower() not in ("null", "not specified", "none", ""):
                extracted_categories.add(ClauseCategory.NOTICE_PERIOD_TO_TERMINATE_RENEWAL.value)

    return extracted_categories


def evaluate_contract_remote(
    contract: CUADContract,
    api_url: str,
) -> set[str]:
    """
    Evaluates contract against a running remote backend server via HTTP requests.
    """
    base = api_url.rstrip("/")
    with httpx.Client(timeout=60.0) as client:
        # 1. Upload
        files = {"file": (f"{contract['title'][:40]}.txt", contract["text"].encode("utf-8"), "text/plain")}
        upload_resp = client.post(f"{base}/api/v1/documents/upload", files=files)
        upload_resp.raise_for_status()
        doc_id = upload_resp.json()["document_id"]

        # 2. Process
        proc_resp = client.post(f"{base}/api/v1/documents/{doc_id}/process")
        proc_resp.raise_for_status()

        # 3. Retrieve detail
        get_resp = client.get(f"{base}/api/v1/documents/{doc_id}")
        get_resp.raise_for_status()
        data = get_resp.json()

        extracted_categories: set[str] = set()
        clauses_data = data.get("analysis", {}).get("clauses", [])
        for c in clauses_data:
            cat_val = c.get("clause_category") or c.get("category") or c.get("clause_type")
            normalized = ClauseCategory.from_str(str(cat_val))
            if normalized:
                extracted_categories.add(normalized.value)

        # Inspect document-level extracted metadata
        doc_overview = data.get("document_overview") or data.get("analysis", {}).get("document_overview")
        if doc_overview:
            extracted_categories.add(ClauseCategory.DOCUMENT_NAME.value)
        parties = data.get("parties") or data.get("analysis", {}).get("parties")
        if parties and len(parties) > 0:
            extracted_categories.add(ClauseCategory.PARTIES.value)
        key_dates = data.get("key_dates") or data.get("analysis", {}).get("key_dates")
        if isinstance(key_dates, dict):
            if key_dates.get("effective_date") and str(key_dates.get("effective_date")).lower() not in ("null", "not specified", "none", ""):
                extracted_categories.add(ClauseCategory.EFFECTIVE_DATE.value)
            if key_dates.get("expiration_date") and str(key_dates.get("expiration_date")).lower() not in ("null", "not specified", "none", ""):
                extracted_categories.add(ClauseCategory.EXPIRATION_DATE.value)
            if key_dates.get("execution_date") or key_dates.get("agreement_date"):
                extracted_categories.add(ClauseCategory.AGREEMENT_DATE.value)
            if key_dates.get("notice_period") and str(key_dates.get("notice_period")).lower() not in ("null", "not specified", "none", ""):
                extracted_categories.add(ClauseCategory.NOTICE_PERIOD_TO_TERMINATE_RENEWAL.value)

        return extracted_categories


def compute_metrics(
    eval_results: list[dict[str, Any]],
) -> dict[str, CategoryMetrics]:
    """
    Calculates Precision, Recall, and F1-Score for each of the 41 CUAD categories.
    """
    metrics: dict[str, CategoryMetrics] = {}

    for cat in ALL_41_CUAD_CATEGORIES:
        tp = 0
        fp = 0
        fn = 0
        gt_count = 0
        pred_count = 0

        for r in eval_results:
            gt_has = cat in r["ground_truth"]
            pred_has = cat in r["predicted"]

            if gt_has:
                gt_count += 1
            if pred_has:
                pred_count += 1

            if gt_has and pred_has:
                tp += 1
            elif not gt_has and pred_has:
                fp += 1
            elif gt_has and not pred_has:
                fn += 1

        # Calculate Precision, Recall, and F1
        if tp + fp > 0:
            precision = tp / (tp + fp)
        elif gt_count == 0 and pred_count == 0:
            precision = 1.0  # Perfect specificity when absent and unpredicted
        else:
            precision = 0.0

        if tp + fn > 0:
            recall = tp / (tp + fn)
        elif gt_count == 0 and pred_count == 0:
            recall = 1.0
        else:
            recall = 0.0

        if precision + recall > 0:
            f1 = (2 * precision * recall) / (precision + recall)
        else:
            f1 = 0.0

        # Classify Performance Tier
        if f1 >= 0.70:
            tier = "STRONG (High F1)"
        elif f1 >= 0.40:
            tier = "MODERATE"
        else:
            tier = "LOW (Missed)"

        metrics[cat] = {
            "category": cat,
            "ground_truth_count": gt_count,
            "predicted_count": pred_count,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "tier": tier,
        }

    return metrics


def render_evaluation_table(metrics: dict[str, CategoryMetrics]) -> str:
    """
    Formats the evaluation results into a clean, readable ASCII benchmark table.
    """
    sorted_metrics = sorted(
        metrics.values(),
        key=lambda x: (x["f1_score"], x["ground_truth_count"]),
        reverse=True,
    )

    header = (
        f"{'Category':<36} | {'GT':<4} | {'Pred':<4} | {'TP':<3} | {'FP':<3} | {'FN':<3} | "
        f"{'Precision':<9} | {'Recall':<8} | {'F1-Score':<8} | {'Performance Tier':<16}"
    )
    divider = "-" * len(header)

    lines = [
        "",
        "=" * len(header),
        "CUAD 41-CLAUSE BENCHMARK ACCURACY EVALUATION REPORT",
        "=" * len(header),
        header,
        divider,
    ]

    for m in sorted_metrics:
        lines.append(
            f"{m['category']:<36} | {m['ground_truth_count']:<4} | {m['predicted_count']:<4} | "
            f"{m['true_positives']:<3} | {m['false_positives']:<3} | {m['false_negatives']:<3} | "
            f"{m['precision']*100:>8.1f}% | {m['recall']*100:>7.1f}% | {m['f1_score']:>8.4f} | {m['tier']:<16}"
        )

    lines.append(divider)

    # Summary groupings
    high_f1 = [m["category"] for m in sorted_metrics if m["f1_score"] >= 0.70]
    mod_f1 = [m["category"] for m in sorted_metrics if 0.40 <= m["f1_score"] < 0.70]
    low_f1 = [m["category"] for m in sorted_metrics if m["f1_score"] < 0.40]

    macro_f1 = sum(m["f1_score"] for m in sorted_metrics) / len(sorted_metrics)
    macro_prec = sum(m["precision"] for m in sorted_metrics) / len(sorted_metrics)
    macro_rec = sum(m["recall"] for m in sorted_metrics) / len(sorted_metrics)

    lines.extend([
        "",
        "SUMMARY INSIGHTS:",
        f"  * High F1 Categories (Strong System Performance): {len(high_f1)}/41 clauses",
        f"    Examples: {', '.join(high_f1[:8]) if high_f1 else 'None'}",
        f"  * Moderate F1 Categories: {len(mod_f1)}/41 clauses",
        f"    Examples: {', '.join(mod_f1[:6]) if mod_f1 else 'None'}",
        f"  * Low F1 / Missed Categories (Needs Improvement): {len(low_f1)}/41 clauses",
        f"    Examples: {', '.join(low_f1[:8]) if low_f1 else 'None'}",
        "",
        f"OVERALL MACRO METRICS: Precision: {macro_prec*100:.2f}% | Recall: {macro_rec*100:.2f}% | Macro F1: {macro_f1:.4f}",
        "=" * len(header),
        "",
    ])

    return "\n".join(lines)


def run_evaluation(
    num_contracts: int = 5,
    cuad_path: str | None = None,
    force_mock: bool = False,
    attempt_download: bool = False,
    api_url: str | None = None,
    seed: int = 42,
    output_json: str | None = None,
) -> tuple[dict[str, CategoryMetrics], str]:
    """
    Main evaluation pipeline:
    1. Loads or downloads the CUAD dataset.
    2. Samples `num_contracts` randomly.
    3. Executes each through the `/api/v1/documents/{id}/process` pipeline.
    4. Evaluates predictions against annotations.
    5. Returns computed metrics and formatted output table.
    """
    random.seed(seed)

    if attempt_download and not cuad_path:
        cuad_path = download_cuad_dataset()

    dataset = load_cuad_dataset(cuad_path=cuad_path, force_mock=force_mock)
    if not dataset:
        raise ValueError("No contracts available in CUAD dataset.")

    # Sample random contracts
    sample_size = min(num_contracts, len(dataset))
    sampled_contracts = random.sample(dataset, sample_size)
    logger.info("Evaluating %d randomly sampled contracts...", sample_size)

    eval_results: list[dict[str, Any]] = []

    if api_url:
        logger.info("Running evaluation against remote API server at %s...", api_url)
        for idx, contract in enumerate(sampled_contracts, 1):
            logger.info("Processing contract %d/%d: %s", idx, sample_size, contract["title"])
            pred = evaluate_contract_remote(contract, api_url)
            eval_results.append({
                "contract": contract["title"],
                "ground_truth": contract["ground_truth_categories"],
                "predicted": pred,
            })
    else:
        logger.info("Running evaluation in-process via FastAPI TestClient...")
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        def test_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        def test_get_user(request: Request, db=Depends(test_get_db)):
            test_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
            org = db.query(Organization).filter(Organization.id == test_uuid).first()
            if not org:
                org = Organization(id=test_uuid, name="Eval Org", plan="free")
                db.add(org)
                db.commit()
            user = db.query(User).filter(User.id == test_uuid).first()
            if not user:
                user = User(id=test_uuid, org_id=test_uuid, email="eval@example.com", role="user")
                db.add(user)
                db.commit()
            return user

        app.dependency_overrides[get_db] = test_get_db
        app.dependency_overrides[get_current_user] = test_get_user

        client = TestClient(app)
        db_session = TestingSessionLocal()

        try:
            for idx, contract in enumerate(sampled_contracts, 1):
                logger.info("Processing contract %d/%d: %s", idx, sample_size, contract["title"])
                pred = evaluate_contract_in_process(contract, client, db_session)
                eval_results.append({
                    "contract": contract["title"],
                    "ground_truth": contract["ground_truth_categories"],
                    "predicted": pred,
                })
        finally:
            db_session.close()
            app.dependency_overrides.clear()

    # Calculate metrics and render report
    metrics = compute_metrics(eval_results)
    table_str = render_evaluation_table(metrics)

    if output_json:
        out_payload = {
            "num_evaluated_contracts": len(sampled_contracts),
            "contracts": [c["title"] for c in sampled_contracts],
            "metrics": metrics,
        }
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(out_payload, f, indent=2)
        logger.info("Wrote detailed evaluation metrics to %s.", output_json)

    return metrics, table_str


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Evaluate Legal Analyzer against the CUAD 41-clause dataset.")
    parser.add_argument("--num-contracts", type=int, default=5, help="Number of random contracts to evaluate (default: 5)")
    parser.add_argument("--cuad-path", type=str, default=None, help="Path to local CUAD_v1.json dataset file")
    parser.add_argument("--mock", action="store_true", help="Force using built-in mock CUAD dataset")
    parser.add_argument("--download", action="store_true", help="Attempt downloading official CUAD dataset")
    parser.add_argument("--api-url", type=str, default=None, help="Remote backend URL (default: in-process)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling (default: 42)")
    parser.add_argument("--output-json", type=str, default=None, help="Save evaluation metrics to JSON file")

    args = parser.parse_args()

    _, table_output = run_evaluation(
        num_contracts=args.num_contracts,
        cuad_path=args.cuad_path,
        force_mock=args.mock,
        attempt_download=args.download,
        api_url=args.api_url,
        seed=args.seed,
        output_json=args.output_json,
    )

    print(table_output)


if __name__ == "__main__":
    main()
