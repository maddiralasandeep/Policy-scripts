import json
import os
import tempfile
import unittest
from unittest.mock import patch

from import_policies import (
    build_policy_delta,
    normalize_policy_name,
    run_migration,
    write_delta_report,
)


class PolicyDeltaTests(unittest.TestCase):
    def test_normalize_policy_name(self):
        self.assertEqual(normalize_policy_name("  Payment   Policy "), "payment policy")
        self.assertEqual(normalize_policy_name("PAYMENT POLICY"), "payment policy")

    def test_delta_contains_only_names_missing_from_target(self):
        source = [
            {"policyId": "1", "displayName": "Existing Policy"},
            {"policyId": "2", "displayName": "New Policy"},
        ]
        target = [{"policyId": "9", "displayName": " existing   policy "}]

        delta, existing, invalid, duplicates = build_policy_delta(source, target)

        self.assertEqual([policy["policyId"] for policy in delta], ["2"])
        self.assertEqual([policy["policyId"] for policy in existing], ["1"])
        self.assertEqual(invalid, [])
        self.assertEqual(duplicates, [])

    def test_invalid_and_duplicate_source_names_are_not_imported(self):
        source = [
            {"policyId": "1", "displayName": "New Policy"},
            {"policyId": "2", "displayName": "NEW POLICY"},
            {"policyId": "3", "displayName": ""},
            {"displayName": "Missing ID"},
        ]

        delta, existing, invalid, duplicates = build_policy_delta(source, [])

        self.assertEqual([policy["policyId"] for policy in delta], ["1"])
        self.assertEqual(existing, [])
        self.assertEqual(len(invalid), 2)
        self.assertEqual([policy["policyId"] for policy in duplicates], ["2"])

    def test_delta_report_is_valid_json(self):
        source = [{"policyId": "1", "displayName": "New Policy"}]
        with tempfile.TemporaryDirectory() as temp_dir:
            report_file = os.path.join(temp_dir, "delta.json")
            report_path = write_delta_report(
                source,
                [],
                source,
                [],
                [],
                [],
                report_file=report_file,
            )

            with open(report_path, encoding="utf-8") as saved_report:
                report = json.load(saved_report)

        self.assertEqual(report["deltaPolicyCount"], 1)
        self.assertEqual(report["deltaPolicies"][0]["displayName"], "New Policy")

    @patch("import_policies.validate_configuration")
    @patch("import_policies.write_delta_report", return_value="/tmp/delta.json")
    @patch("import_policies.import_policy")
    @patch("import_policies.get_all_policies")
    @patch("import_policies.get_token", side_effect=["stg-token", "prod-token"])
    def test_dry_run_compares_both_environments_without_importing(
        self,
        _get_token,
        get_all_policies,
        import_policy,
        _write_delta_report,
        _validate_configuration,
    ):
        get_all_policies.side_effect = [
            [{"policyId": "1", "displayName": "New Policy", "structuredRego": "x"}],
            [],
        ]

        run_migration(dry_run=True)

        self.assertEqual(_get_token.call_count, 2)
        self.assertEqual(_get_token.call_args_list[0].args[2], "STG")
        self.assertEqual(_get_token.call_args_list[1].args[2], "PROD")
        self.assertEqual(get_all_policies.call_count, 2)
        self.assertEqual(get_all_policies.call_args_list[0].kwargs["environment_name"], "STG")
        self.assertEqual(get_all_policies.call_args_list[1].kwargs["environment_name"], "PROD")
        import_policy.assert_not_called()


if __name__ == "__main__":
    unittest.main()