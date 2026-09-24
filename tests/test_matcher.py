import unittest

from matcher import education_level, extract_skills, extract_years, rank_resumes, score_resume
from repository import load_jobs, load_resumes


class MatcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jobs = load_jobs()
        cls.resumes = load_resumes()

    def test_extract_skills_supports_aliases(self):
        skills = extract_skills("熟悉 Python、Vue3、SpringBoot 和自然语言处理")
        self.assertIn("Python", skills)
        self.assertIn("Vue", skills)
        self.assertIn("Spring Boot", skills)
        self.assertIn("NLP", skills)

    def test_extract_years_uses_maximum_valid_value(self):
        self.assertEqual(extract_years("1年实习，另有2.5 years项目经验"), 2.5)

    def test_education_level_is_ordered(self):
        self.assertGreater(education_level("硕士研究生"), education_level("本科"))
        self.assertGreater(education_level("本科"), education_level("大专"))

    def test_score_is_bounded_and_explainable(self):
        job = next(item for item in self.jobs if item["job_id"] == "J001")
        resume = next(item for item in self.resumes if item["resume_id"] == "R001")
        result = score_resume(resume["full_text"], job)
        self.assertGreaterEqual(result["total_score"], 0)
        self.assertLessEqual(result["total_score"], 100)
        self.assertIn("Python", result["matched_skills"])
        self.assertIn("scores", result)

    def test_empty_resume_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "不能为空"):
            score_resume("  ", self.jobs[0])

    def test_best_java_candidate_ranks_first(self):
        job = next(item for item in self.jobs if item["job_id"] == "J005")
        ranked = rank_resumes(self.resumes, job)
        self.assertEqual(ranked[0]["resume_id"], "R013")
        self.assertEqual([item["rank"] for item in ranked[:3]], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
