import unittest

from repository import load_ground_truth, load_jobs, load_resumes


class RepositoryTests(unittest.TestCase):
    def test_dataset_counts_and_unique_ids(self):
        jobs = load_jobs()
        resumes = load_resumes()
        self.assertEqual(len(jobs), 6)
        self.assertEqual(len(resumes), 18)
        self.assertEqual(len({item["job_id"] for item in jobs}), len(jobs))
        self.assertEqual(len({item["resume_id"] for item in resumes}), len(resumes))

    def test_every_job_has_ground_truth(self):
        jobs = load_jobs()
        truth = load_ground_truth()
        self.assertTrue(all(job["job_id"] in truth for job in jobs))
        self.assertTrue(all(len(values) >= 1 for values in truth.values()))


if __name__ == "__main__":
    unittest.main()
