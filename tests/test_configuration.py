from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate


class ConfigurationTests(unittest.TestCase):
    def check_environment(self, overrides, valid=False):
        environment = validate.FIXTURE | overrides
        result = validate.validate_startup(environment)
        self.assertEqual(result.returncode, 0 if valid else 64, result.stderr)
        if environment.get("ACCESS_TOKEN"):
            self.assertNotIn(environment["ACCESS_TOKEN"], result.stdout + result.stderr)

    def test_blueprint_contract(self):
        validate.validate_project()

    def test_repo(self):
        self.check_environment({}, valid=True)

    def test_org(self):
        self.check_environment({"RUNNER_SCOPE": "org", "ORG_NAME": "example-org",
                                "REPO_URL": "", "RUNNER_GROUP": "Trusted Builds"}, valid=True)

    def test_invalid_inputs(self):
        cases = [
            {"ACCESS_TOKEN": ""}, {"ACCESS_TOKEN": "changeme"},
            {"ACCESS_TOKEN": "${ACCESS_TOKEN}"}, {"ACCESS_TOKEN": "token with spaces"},
            {"ACCESS_TOKEN": "'quoted_token'"}, {"ACCESS_TOKEN": "line1\nline2"},
            {"ACCESS_TOKEN": "$(touch /tmp/dokploy-runner-should-never-exist)"},
            {"RUNNER_SCOPE": ""}, {"RUNNER_SCOPE": "ORG"}, {"RUNNER_SCOPE": "enterprise"},
            {"RUNNER_NAME": ""}, {"RUNNER_NAME": "name with spaces"},
            {"RUNNER_NAME": "x" * 65}, {"RUNNER_NAME": "--option"},
            {"LABELS": ""}, {"LABELS": "dokploy, other"}, {"LABELS": "dokploy,"},
            {"LABELS": "a,,b"}, {"LABELS": "a\nb"},
            {"RUNNER_GROUP": "-group"}, {"RUNNER_GROUP": "group\nother"},
            {"REPO_URL": ""}, {"REPO_URL": "http://github.com/example/project"},
            {"REPO_URL": "https://github.com/example/project.git"},
            {"REPO_URL": "https://github.com/example/project/"},
            {"REPO_URL": "https://github.com/example/project?token=secret"},
            {"REPO_URL": "https://github.example.com/example/project"},
            {"REPO_URL": "https://github.com/example"}, {"ORG_NAME": "ambiguous"},
            {"RUNNER_GROUP": "custom-repo-group"},
            {"RUNNER_SCOPE": "org", "ORG_NAME": "", "REPO_URL": ""},
            {"RUNNER_SCOPE": "org", "ORG_NAME": "https://github.com/example", "REPO_URL": ""},
            {"RUNNER_SCOPE": "org", "ORG_NAME": "example"},
        ]
        for case in cases:
            with self.subTest(keys=list(case), case_number=cases.index(case)):
                self.check_environment(case)

    def test_missing_required_compose_inputs(self):
        for key in ("ACCESS_TOKEN", "RUNNER_SCOPE", "RUNNER_NAME", "LABELS"):
            for mode in ("missing", "empty"):
                with self.subTest(key=key, mode=mode):
                    values = validate.FIXTURE.copy()
                    if mode == "missing":
                        del values[key]
                    else:
                        values[key] = ""
                    with self.assertRaises(ValueError):
                        validate.compose_config(values)

    def test_dokploy_env_file_forwarding_and_allowlist(self):
        # Shell contains no fixture variables: only .env can supply the token.
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("\n".join(f"{key}={value}" for key, value in validate.FIXTURE.items()) +
                                "\nUNRELATED_SECRET=do_not_forward\nDEBUG_OUTPUT=true\n"
                                "RUN_AS_ROOT=true\nSTART_DOCKER_SERVICE=true\nEPHEMERAL=false\nDISABLE_AUTO_UPDATE=true\nPATH=/untrusted\n")
            config = validate.compose_config(env_file=env_file)
            environment = config["services"]["dokploy-actions-runner"]["environment"]
            self.assertEqual(environment["ACCESS_TOKEN"], validate.FIXTURE["ACCESS_TOKEN"])
            self.assertEqual(environment["RUN_AS_ROOT"], "false")
            self.assertEqual(environment["START_DOCKER_SERVICE"], "false")
            self.assertNotIn("UNRELATED_SECRET", environment)
            self.assertNotIn("DEBUG_OUTPUT", environment)
            self.assertNotIn("EPHEMERAL", environment)
            self.assertNotIn("DISABLE_AUTO_UPDATE", environment)
            self.assertTrue(environment["PATH"].startswith("/actions-runner/externals/node24/bin:"))
            # Compose's rendered config escapes dollars for serialization. Verify
            # the startup validation separately with the real environment values.
            self.assertEqual(validate.validate_startup(environment).returncode, 0)

    def test_independent_projects(self):
        first = validate.compose_config(validate.FIXTURE, project="runner-one")
        second = validate.compose_config(validate.FIXTURE | {"RUNNER_NAME": "runner-two", "LABELS": "other"}, project="runner-two")
        a, b = (config["services"]["dokploy-actions-runner"] for config in (first, second))
        self.assertNotEqual(first["name"], second["name"])
        self.assertNotEqual(a["environment"]["RUNNER_NAME"], b["environment"]["RUNNER_NAME"])
        self.assertNotEqual(a["environment"]["LABELS"], b["environment"]["LABELS"])
        self.assertNotIn("volumes", a)
        self.assertNotIn("container_name", a)

    def test_generated_name_is_valid(self):
        self.check_environment({"RUNNER_NAME": "dokploy-12345678-1234-1234-1234-123456789abc"}, valid=True)

    def test_validator_never_echoes_invalid_token(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            values = validate.FIXTURE | {"ACCESS_TOKEN": "sensitive bad token"}
            env_file.write_text("\n".join(f"{key}='{value}'" for key, value in values.items()))
            result = subprocess.run([sys.executable, str(validate.ROOT / "scripts/validate.py"),
                                     "--env-file", str(env_file)], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(values["ACCESS_TOKEN"], result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
