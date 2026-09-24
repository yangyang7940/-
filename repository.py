"""CSV 数据访问与校验。"""

from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"数据文件不存在：{path}")
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return [dict(row) for row in csv.DictReader(file)]


def resume_to_text(resume: dict[str, object]) -> str:
    """将结构化简历拼接为算法输入文本。"""

    return "；".join(
        f"{label}：{resume.get(field, '')}"
        for field, label in (
            ("target_role", "求职方向"),
            ("years", "经验"),
            ("education", "学历"),
            ("skills", "技能"),
            ("summary", "个人简介"),
            ("experience", "项目经历"),
        )
    )


def load_jobs() -> list[dict[str, str]]:
    jobs = _read_csv(DATA_DIR / "jobs.csv")
    required = {"job_id", "title", "description", "required_skills", "min_years", "min_education"}
    if jobs and not required.issubset(jobs[0]):
        raise ValueError("岗位数据缺少必要字段")
    return jobs


def load_resumes() -> list[dict[str, str]]:
    resumes = _read_csv(DATA_DIR / "resumes.csv")
    required = {"resume_id", "name", "target_role", "years", "education", "skills", "summary", "experience"}
    if resumes and not required.issubset(resumes[0]):
        raise ValueError("简历数据缺少必要字段")
    for resume in resumes:
        resume["full_text"] = resume_to_text(resume)
    return resumes


def load_ground_truth() -> dict[str, set[str]]:
    rows = _read_csv(DATA_DIR / "ground_truth.csv")
    return {
        row["job_id"]: {value.strip() for value in row["relevant_resume_ids"].split("|") if value.strip()}
        for row in rows
    }
