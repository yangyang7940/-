"""在标注测试集上计算 Top-1、Precision@3 和 Recall@3。"""

from __future__ import annotations

import json
from pathlib import Path

from matcher import rank_resumes
from repository import PROJECT_ROOT, load_ground_truth, load_jobs, load_resumes


def evaluate() -> dict[str, object]:
    jobs = load_jobs()
    resumes = load_resumes()
    truth = load_ground_truth()
    details: list[dict[str, object]] = []
    top1_hits = 0
    precision_values: list[float] = []
    recall_values: list[float] = []

    for job in jobs:
        relevant = truth.get(job["job_id"], set())
        ranked = rank_resumes(resumes, job)
        top3 = [str(item["resume_id"]) for item in ranked[:3]]
        hits = len(set(top3) & relevant)
        top1_hit = bool(top3 and top3[0] in relevant)
        top1_hits += int(top1_hit)
        precision_values.append(hits / 3)
        recall_values.append(hits / len(relevant) if relevant else 0.0)
        details.append(
            {
                "job_id": job["job_id"],
                "title": job["title"],
                "top3": top3,
                "relevant": sorted(relevant),
                "top1_hit": top1_hit,
            }
        )

    job_count = len(jobs) or 1
    return {
        "job_count": len(jobs),
        "resume_count": len(resumes),
        "top1_accuracy": round(top1_hits / job_count, 4),
        "precision_at_3": round(sum(precision_values) / job_count, 4),
        "recall_at_3": round(sum(recall_values) / job_count, 4),
        "details": details,
    }


def main() -> None:
    result = evaluate()
    output_path = Path(PROJECT_ROOT) / "docs" / "evaluation_results.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n结果已保存：{output_path}")


if __name__ == "__main__":
    main()
