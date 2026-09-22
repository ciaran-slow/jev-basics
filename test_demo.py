import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from demo import load_env, validate_response


class EnvTests(unittest.TestCase):
    def test_reads_file_without_replacing_shell(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, ".env")
            path.write_text('# key\nOPENROUTER_API_KEY="from-file"\nexport OTHER=x\n')
            with mock.patch.dict(os.environ, {"OTHER": "shell"}, clear=True):
                load_env(path)
                self.assertEqual(os.environ["OPENROUTER_API_KEY"], "from-file")
                self.assertEqual(os.environ["OTHER"], "shell")

    def test_missing_file(self):
        load_env(Path("/nonexistent/.env"))


class ResponseTests(unittest.TestCase):
    def setUp(self):
        self.data = {"answers": {
            name: {"choice": "unknown", "confidence": 0.5,
                   "probabilities": {"yes": 0.2, "no": 0.2, "unknown": 0.6}}
            for name in ("remote_nz", "mentoring")
        }}

    def test_valid(self):
        self.assertEqual(validate_response(self.data), self.data)

    def test_missing_answer(self):
        del self.data["answers"]["mentoring"]
        with self.assertRaises(ValueError):
            validate_response(self.data)

    def test_bad_choice(self):
        self.data["answers"]["remote_nz"]["choice"] = "maybe"
        with self.assertRaises(ValueError):
            validate_response(self.data)

    def test_bad_confidence(self):
        for value in (True, "0.5", -1, 2, float("nan")):
            with self.subTest(value=value):
                data = copy.deepcopy(self.data)
                data["answers"]["remote_nz"]["confidence"] = value
                with self.assertRaises(ValueError):
                    validate_response(data)

    def test_bad_probabilities(self):
        self.data["answers"]["remote_nz"]["probabilities"]["yes"] = 0.9
        with self.assertRaises(ValueError):
            validate_response(self.data)


if __name__ == "__main__":
    unittest.main()
