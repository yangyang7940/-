"""智能简历筛选系统的核心匹配算法。

该模块只使用 Python 标准库，便于在离线答辩环境中运行。算法综合考虑：
文本语义相似度、技能覆盖率、工作经验和学历要求。
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable, Sequence


SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python", "py语言"),
    "Java": ("java",),
    "C++": ("c++", "cpp"),
    "JavaScript": ("javascript", "js", "es6"),
    "TypeScript": ("typescript", "ts"),
    "HTML/CSS": ("html", "css", "前端页面"),
    "Vue": ("vue", "vue.js", "vue3"),
    "React": ("react", "react.js"),
    "Spring Boot": ("spring boot", "springboot"),
    "Flask": ("flask",),
    "Django": ("django",),
    "SQL": ("sql", "数据库查询"),
    "MySQL": ("mysql",),
    "PostgreSQL": ("postgresql", "postgres"),
    "Redis": ("redis",),
    "Git": ("git", "版本控制"),
    "Docker": ("docker", "容器化"),
    "Linux": ("linux",),
    "数据分析": ("数据分析", "data analysis", "数据洞察"),
    "Pandas": ("pandas",),
    "NumPy": ("numpy",),
    "Matplotlib": ("matplotlib", "数据可视化"),
    "机器学习": ("机器学习", "machine learning", "ml"),
    "深度学习": ("深度学习", "deep learning", "dl"),
    "Scikit-learn": ("scikit-learn", "sklearn"),
    "PyTorch": ("pytorch", "torch"),
    "TensorFlow": ("tensorflow",),
    "NLP": ("nlp", "自然语言处理"),
    "大语言模型": ("大语言模型", "llm", "langchain", "prompt"),
    "OpenCV": ("opencv", "计算机视觉"),
    "推荐系统": ("推荐系统", "协同过滤", "recommendation"),
    "Excel": ("excel", "电子表格"),
    "Power BI": ("power bi", "powerbi"),
    "Axure": ("axure", "原型设计"),
    "产品运营": ("产品运营", "用户运营", "活动运营"),
    "需求分析": ("需求分析", "用户需求", "需求文档", "prd"),
    "A/B测试": ("a/b测试", "ab测试", "a/b test"),
    "数据结构": ("数据结构", "算法基础"),
    "RESTful API": ("restful", "rest api", "接口开发"),
    "微服务": ("微服务", "microservice"),
}

EDUCATION_LEVELS = {
    "不限": 0,
    "中专": 1,
    "高中": 1,
    "专科": 2,
    "大专": 2,
    "本科": 3,
    "学士": 3,
    "硕士": 4,
    "研究生": 4,
    "博士": 5,
}

_ENGLISH_TOKEN_RE = re.compile(r"[a-z][a-z0-9+#.\-/]*|\d+(?:\.\d+)?", re.I)
_CHINESE_SEQUENCE_RE = re.compile(r"[\u4e00-\u9fff]+")
_YEAR_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:年|years?|yrs?)", re.I)


def normalize_text(text: object) -> str:
    """统一大小写、空白和常见全角符号。"""

    value = "" if text is None else str(text)
    translation = str.maketrans({"＋": "+", "＃": "#", "／": "/", "，": ","})
    return re.sub(r"\s+", " ", value.translate(translation).lower()).strip()


def extract_skills(text: object) -> list[str]:
    """通过可解释的技能词典从非结构化文本中提取技能。"""

    normalized = normalize_text(text)
    found: list[str] = []
    for canonical, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            escaped = re.escape(alias.lower())
            if re.fullmatch(r"[a-z0-9+#.\-/ ]+", alias.lower()):
                pattern = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
                if re.search(pattern, normalized):
                    found.append(canonical)
                    break
            elif alias.lower() in normalized:
                found.append(canonical)
                break
    return found


def extract_years(text: object) -> float:
    """提取文本中最大的年限数字。"""

    values = [float(value) for value in _YEAR_RE.findall(normalize_text(text))]
    return max(values, default=0.0)


def education_level(text: object) -> int:
    """将学历转换为有序等级，取文本中出现的最高学历。"""

    normalized = normalize_text(text)
    return max((level for name, level in EDUCATION_LEVELS.items() if name in normalized), default=0)


def tokenize(text: object) -> list[str]:
    """中英文混合分词。

    英文按单词切分；中文增加单字、二元和三元片段，使系统无需额外分词库。
    """

    normalized = normalize_text(text)
    tokens = _ENGLISH_TOKEN_RE.findall(normalized)
    for sequence in _CHINESE_SEQUENCE_RE.findall(normalized):
        tokens.extend(sequence)
        tokens.extend(sequence[index : index + 2] for index in range(len(sequence) - 1))
        tokens.extend(sequence[index : index + 3] for index in range(len(sequence) - 2))
    tokens.extend(f"skill:{skill.lower()}" for skill in extract_skills(normalized))
    return [token for token in tokens if token]


def semantic_similarities(query: object, documents: Sequence[object]) -> list[float]:
    """计算查询文本与一组文档的 TF-IDF 余弦相似度（0~100）。"""

    if not documents:
        return []
    tokenized = [tokenize(query), *(tokenize(document) for document in documents)]
    document_count = len(tokenized)
    frequencies = [Counter(tokens) for tokens in tokenized]
    doc_frequency = Counter()
    for tokens in tokenized:
        doc_frequency.update(set(tokens))

    def vector(counter: Counter[str]) -> dict[str, float]:
        total = sum(counter.values()) or 1
        return {
            token: (count / total) * (math.log((1 + document_count) / (1 + doc_frequency[token])) + 1)
            for token, count in counter.items()
        }

    vectors = [vector(counter) for counter in frequencies]
    query_vector = vectors[0]
    query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
    scores: list[float] = []
    for doc_vector in vectors[1:]:
        doc_norm = math.sqrt(sum(value * value for value in doc_vector.values()))
        if not query_norm or not doc_norm:
            scores.append(0.0)
            continue
        dot_product = sum(value * doc_vector.get(token, 0.0) for token, value in query_vector.items())
        scores.append(round(100 * dot_product / (query_norm * doc_norm), 2))
    return scores


def _required_skills(job: dict[str, object]) -> list[str]:
    fields = " ".join(str(job.get(key, "")) for key in ("description", "required_skills", "title"))
    return extract_skills(fields)


def _job_text(job: dict[str, object]) -> str:
    return " ".join(
        str(job.get(key, ""))
        for key in ("title", "description", "required_skills", "min_years", "min_education")
    )


def _safe_float(value: object) -> float:
    try:
        return float(str(value).strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def score_resume(
    resume_text: str,
    job: dict[str, object],
    *,
    semantic_score: float | None = None,
) -> dict[str, object]:
    """计算单份简历的四维匹配结果并返回可解释结论。"""

    if not normalize_text(resume_text):
        raise ValueError("简历内容不能为空")

    required_skills = _required_skills(job)
    resume_skills = extract_skills(resume_text)
    matched_skills = [skill for skill in required_skills if skill in resume_skills]
    missing_skills = [skill for skill in required_skills if skill not in resume_skills]

    if semantic_score is None:
        semantic_score = semantic_similarities(_job_text(job), [resume_text])[0]
    skill_score = 100.0 * len(matched_skills) / len(required_skills) if required_skills else 100.0

    required_years = _safe_float(job.get("min_years", 0))
    resume_years = extract_years(resume_text)
    experience_score = 100.0 if required_years <= 0 else min(100.0, 100.0 * resume_years / required_years)

    required_education = education_level(job.get("min_education", ""))
    resume_education = education_level(resume_text)
    education_score = (
        100.0
        if required_education <= 0
        else min(100.0, 100.0 * resume_education / required_education)
    )

    total = round(
        semantic_score * 0.40
        + skill_score * 0.35
        + experience_score * 0.15
        + education_score * 0.10,
        1,
    )
    if total >= 80:
        recommendation = "高度匹配"
        decision = "建议优先进入面试"
    elif total >= 65:
        recommendation = "较匹配"
        decision = "建议进入初筛"
    elif total >= 50:
        recommendation = "可考虑"
        decision = "建议结合项目经历复核"
    else:
        recommendation = "暂不匹配"
        decision = "建议保留人才库"

    strengths: list[str] = []
    risks: list[str] = []
    if matched_skills:
        strengths.append(f"覆盖 {len(matched_skills)}/{len(required_skills)} 项岗位技能")
    if resume_years >= required_years:
        strengths.append("工作/项目年限达到岗位要求")
    elif required_years:
        risks.append(f"年限低于要求 {round(required_years - resume_years, 1):g} 年")
    if resume_education >= required_education:
        strengths.append("学历达到岗位要求")
    elif required_education:
        risks.append("学历未达到岗位最低要求")
    if missing_skills:
        risks.append("待补充技能：" + "、".join(missing_skills[:5]))

    return {
        "total_score": total,
        "recommendation": recommendation,
        "decision": decision,
        "scores": {
            "semantic": round(float(semantic_score), 1),
            "skill": round(skill_score, 1),
            "experience": round(experience_score, 1),
            "education": round(education_score, 1),
        },
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "resume_skills": resume_skills,
        "required_skills": required_skills,
        "resume_years": resume_years,
        "required_years": required_years,
        "strengths": strengths or ["简历包含与岗位相关的有效信息"],
        "risks": risks or ["未发现明显硬性条件缺口"],
    }


def rank_resumes(
    resumes: Iterable[dict[str, object]],
    job: dict[str, object],
) -> list[dict[str, object]]:
    """按综合得分从高到低排序候选人。"""

    resume_list = list(resumes)
    texts = [str(resume.get("full_text", "")) for resume in resume_list]
    semantic_scores = semantic_similarities(_job_text(job), texts)
    ranked: list[dict[str, object]] = []
    for resume, semantic_score in zip(resume_list, semantic_scores):
        result = score_resume(str(resume.get("full_text", "")), job, semantic_score=semantic_score)
        ranked.append(
            {
                "resume_id": resume.get("resume_id", ""),
                "name": resume.get("name", "匿名候选人"),
                "target_role": resume.get("target_role", ""),
                **result,
            }
        )
    ranked.sort(key=lambda item: (-float(item["total_score"]), str(item["resume_id"])))
    for index, item in enumerate(ranked, 1):
        item["rank"] = index
    return ranked
