"""
test_ec2_controller.py

Self-contained, simulated test suite for aws/ec2_controller.py.

This file does NOT touch real AWS. It stubs out boto3 and your project's
config/monitoring modules in-memory, then imports ec2_controller and drives
it against a small fake EC2 backend that tracks instance state/type and
remembers what API calls were made (stop/start/modify).

HOW TO RUN
----------
1. Drop this file anywhere in your project root (next to aws/, backend/).
2. Run:  python -m pytest test_ec2_controller.py -v
   (or just `python test_ec2_controller.py` to run without pytest)

No AWS credentials, network access, or real boto3 client calls are needed.
"""

import os
import sys
import time
import types
import importlib
import unittest
from unittest.mock import MagicMock

# Directory this test file lives in (assumed to be the project root,
# i.e. the parent of the real aws/ package).
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# 1. Build a fake in-memory EC2 "AWS backend" before ec2_controller is imported
# ---------------------------------------------------------------------------

class FakeEC2Backend:
    """Tracks a single fake instance's state/type and call history."""

    def __init__(self, instance_id, instance_type, state="stopped"):
        self.instance_id = instance_id
        self.instance_type = instance_type
        self.state = state
        self.calls = []  # list of (method_name, kwargs) for assertions

        # fail_on lets a test force a specific call to raise, to test
        # the except/raise branches in ec2_controller.
        self.fail_on = None  # e.g. "modify_instance_attribute"

    def _maybe_fail(self, method_name):
        if self.fail_on == method_name:
            raise RuntimeError(f"Simulated AWS failure on {method_name}")

    def describe_instances(self, InstanceIds):
        self.calls.append(("describe_instances", {"InstanceIds": InstanceIds}))
        self._maybe_fail("describe_instances")
        assert InstanceIds == [self.instance_id]
        return {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceType": self.instance_type,
                            "State": {"Name": self.state},
                        }
                    ]
                }
            ]
        }

    def modify_instance_attribute(self, InstanceId, InstanceType):
        self.calls.append(
            ("modify_instance_attribute", {"InstanceId": InstanceId, "InstanceType": InstanceType})
        )
        self._maybe_fail("modify_instance_attribute")
        assert InstanceId == self.instance_id
        self.instance_type = InstanceType["Value"]

    def start_instances(self, InstanceIds):
        self.calls.append(("start_instances", {"InstanceIds": InstanceIds}))
        self._maybe_fail("start_instances")
        self.state = "running"

    def stop_instances(self, InstanceIds):
        self.calls.append(("stop_instances", {"InstanceIds": InstanceIds}))
        self._maybe_fail("stop_instances")
        self.state = "stopped"

    def get_waiter(self, name):
        # waiter.wait(...) is a no-op since stop/start already update state
        backend = self
        waiter = MagicMock()

        def _wait(InstanceIds=None):
            backend.calls.append((f"waiter[{name}].wait", {"InstanceIds": InstanceIds}))

        waiter.wait.side_effect = _wait
        return waiter


INSTANCE_ID = "i-0123456789abcdef0"
INSTANCE_SEQUENCE = ["t2.micro", "t2.small", "t2.medium", "t2.large"]


def install_fake_modules(backend, dry_run=False):
    """
    Stub out boto3 + the project's aws.aws_config / backend.config /
    aws.monitoring_setup modules in sys.modules, so importing
    aws.ec2_controller pulls in our fakes instead of the real AWS SDK
    or your real project config.
    """

    # --- fake boto3 ---
    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.client = MagicMock(return_value=backend)
    sys.modules["boto3"] = fake_boto3

    # --- fake aws package + aws.aws_config ---
    # __path__ must point at the REAL aws/ directory on disk so that
    # `import aws.ec2_controller` still finds your real source file;
    # only aws_config and monitoring_setup are swapped for fakes.
    fake_aws_pkg = types.ModuleType("aws")
    fake_aws_pkg.__path__ = [os.path.join(PROJECT_ROOT, "aws")]
    sys.modules["aws"] = fake_aws_pkg

    fake_aws_config = types.ModuleType("aws.aws_config")
    fake_aws_config.AWS_REGION = "us-east-1"
    fake_aws_config.INSTANCE_ID = INSTANCE_ID
    fake_aws_config.INSTANCE_SEQUENCE = INSTANCE_SEQUENCE
    sys.modules["aws.aws_config"] = fake_aws_config

    # --- fake backend package + backend.config ---
    fake_backend_pkg = types.ModuleType("backend")
    fake_backend_pkg.__path__ = [os.path.join(PROJECT_ROOT, "backend")]
    sys.modules["backend"] = fake_backend_pkg

    fake_backend_config = types.ModuleType("backend.config")
    fake_backend_config.DRY_RUN = dry_run
    sys.modules["backend.config"] = fake_backend_config

    # --- fake aws.monitoring_setup ---
    fake_monitoring = types.ModuleType("aws.monitoring_setup")
    fake_monitoring.setup_monitoring_on_instance = MagicMock()
    sys.modules["aws.monitoring_setup"] = fake_monitoring

    return fake_monitoring


def load_ec2_controller(backend, dry_run=False):
    """Fresh import of ec2_controller wired to the given fake backend."""
    install_fake_modules(backend, dry_run=dry_run)
    if "aws.ec2_controller" in sys.modules:
        del sys.modules["aws.ec2_controller"]
    module = importlib.import_module("aws.ec2_controller")
    return module


# ---------------------------------------------------------------------------
# 2. Test cases
# ---------------------------------------------------------------------------

class TestGetInstanceType(unittest.TestCase):
    def test_returns_type_and_state(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.small", state="running")
        ctrl = load_ec2_controller(backend)
        itype, state = ctrl.get_instance_type()
        self.assertEqual(itype, "t2.small")
        self.assertEqual(state, "running")

    def test_describe_failure_raises(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.small")
        backend.fail_on = "describe_instances"
        ctrl = load_ec2_controller(backend)
        with self.assertRaises(Exception):
            ctrl.get_instance_type()


class TestChangeInstanceType(unittest.TestCase):
    def test_blocked_when_running(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.small", state="running")
        ctrl = load_ec2_controller(backend)
        with self.assertRaises(ValueError):
            ctrl.change_instance_type("t2.medium")

    def test_noop_when_same_type(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.small", state="stopped")
        ctrl = load_ec2_controller(backend)
        result = ctrl.change_instance_type("t2.small")
        self.assertFalse(result["success"])
        self.assertIn("already at", result["reason"])

    def test_dry_run_does_not_call_aws_mutation(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.small", state="stopped")
        ctrl = load_ec2_controller(backend, dry_run=True)
        result = ctrl.change_instance_type("t2.medium")
        self.assertTrue(result["success"])
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["old_type"], "t2.small")
        self.assertEqual(result["new_type"], "t2.medium")
        # No modify/start calls should have happened
        called_methods = [c[0] for c in backend.calls]
        self.assertNotIn("modify_instance_attribute", called_methods)
        self.assertNotIn("start_instances", called_methods)

    def test_successful_scale_modifies_starts_and_sets_up_monitoring(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.small", state="stopped")
        ctrl = load_ec2_controller(backend, dry_run=False)
        result = ctrl.change_instance_type("t2.medium")

        self.assertTrue(result["success"])
        self.assertFalse(result["dry_run"])
        self.assertEqual(result["old_type"], "t2.small")
        self.assertEqual(result["new_type"], "t2.medium")
        self.assertEqual(backend.instance_type, "t2.medium")
        self.assertEqual(backend.state, "running")

        called_methods = [c[0] for c in backend.calls]
        self.assertIn("modify_instance_attribute", called_methods)
        self.assertIn("start_instances", called_methods)
        self.assertIn("waiter[instance_running].wait", called_methods)

        # monitoring setup should have been called with the instance id
        ctrl.setup_monitoring_on_instance.assert_called_once_with(INSTANCE_ID)

    def test_monitoring_failure_does_not_fail_the_scale(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.small", state="stopped")
        ctrl = load_ec2_controller(backend, dry_run=False)
        ctrl.setup_monitoring_on_instance.side_effect = RuntimeError("monitoring down")

        result = ctrl.change_instance_type("t2.medium")
        # Scaling itself should still report success even though monitoring failed
        self.assertTrue(result["success"])

    def test_modify_failure_raises(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.small", state="stopped")
        backend.fail_on = "modify_instance_attribute"
        ctrl = load_ec2_controller(backend, dry_run=False)
        with self.assertRaises(Exception):
            ctrl.change_instance_type("t2.medium")


class TestScaleUp(unittest.TestCase):
    def test_scale_up_from_running_stops_then_scales(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.small", state="running")
        ctrl = load_ec2_controller(backend, dry_run=False)
        result = ctrl.scale_up()

        self.assertTrue(result["success"])
        self.assertEqual(result["old_type"], "t2.small")
        self.assertEqual(result["new_type"], "t2.medium")
        self.assertEqual(backend.instance_type, "t2.medium")
        self.assertEqual(backend.state, "running")  # stopped, scaled, then restarted

        called_methods = [c[0] for c in backend.calls]
        # Must stop before modifying
        self.assertLess(
            called_methods.index("stop_instances"),
            called_methods.index("modify_instance_attribute"),
        )

    def test_scale_up_already_stopped_skips_extra_stop(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.small", state="stopped")
        ctrl = load_ec2_controller(backend, dry_run=False)
        ctrl.scale_up()
        called_methods = [c[0] for c in backend.calls]
        self.assertNotIn("stop_instances", called_methods)

    def test_scale_up_at_max_returns_failure_without_calls(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.large", state="stopped")
        ctrl = load_ec2_controller(backend, dry_run=False)
        result = ctrl.scale_up()
        self.assertFalse(result["success"])
        self.assertIn("maximum", result["reason"])
        self.assertEqual(backend.instance_type, "t2.large")

    def test_scale_up_dry_run_does_not_stop_running_instance(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.small", state="running")
        ctrl = load_ec2_controller(backend, dry_run=True)
        result = ctrl.scale_up()
        self.assertTrue(result["dry_run"])
        called_methods = [c[0] for c in backend.calls]
        self.assertNotIn("stop_instances", called_methods)
        # instance should remain untouched/running in dry run
        self.assertEqual(backend.state, "running")

    def test_scale_up_unknown_type_raises(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.nano", state="stopped")
        ctrl = load_ec2_controller(backend, dry_run=False)
        with self.assertRaises(ValueError):
            ctrl.scale_up()


class TestScaleDown(unittest.TestCase):
    def test_scale_down_from_running_stops_then_scales(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.medium", state="running")
        ctrl = load_ec2_controller(backend, dry_run=False)
        result = ctrl.scale_down()

        self.assertTrue(result["success"])
        self.assertEqual(result["old_type"], "t2.medium")
        self.assertEqual(result["new_type"], "t2.small")
        self.assertEqual(backend.instance_type, "t2.small")

    def test_scale_down_at_min_returns_failure(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.micro", state="stopped")
        ctrl = load_ec2_controller(backend, dry_run=False)
        result = ctrl.scale_down()
        self.assertFalse(result["success"])
        self.assertIn("minimum", result["reason"])

    def test_scale_down_dry_run(self):
        backend = FakeEC2Backend(INSTANCE_ID, "t2.medium", state="stopped")
        ctrl = load_ec2_controller(backend, dry_run=True)
        result = ctrl.scale_down()
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["new_type"], "t2.small")
        self.assertEqual(backend.instance_type, "t2.medium")  # untouched

    def test_scale_down_unknown_type_raises(self):
        backend = FakeEC2Backend(INSTANCE_ID, "weird.type", state="stopped")
        ctrl = load_ec2_controller(backend, dry_run=False)
        with self.assertRaises(ValueError):
            ctrl.scale_down()


# ---------------------------------------------------------------------------
# 3. Pytest-style colored TUI runner (used when run directly, no pytest needed)
# ---------------------------------------------------------------------------

class _Colors:
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    GREY = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        for attr in ("GREEN", "RED", "YELLOW", "CYAN", "GREY", "BOLD", "RESET"):
            setattr(cls, attr, "")


if not sys.stdout.isatty():
    _Colors.disable()


class TUITestResult(unittest.TestResult):
    """Collects results per-test so we can render a pytest-like report."""

    def __init__(self):
        super().__init__()
        self.results = []  # list of (test, outcome, detail)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.results.append((test, "PASSED", None))

    def addError(self, test, err):
        super().addError(test, err)
        self.results.append((test, "ERROR", self._exc_info_to_string(err, test)))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.results.append((test, "FAILED", self._exc_info_to_string(err, test)))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.results.append((test, "SKIPPED", reason))


def run_tui():
    """Run all tests with a pytest-like colored progress bar + summary."""
    import logging
    logging.disable(logging.CRITICAL)  # silence ec2_controller's own log calls

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    tests = []

    def _flatten(s):
        for item in s:
            if isinstance(item, unittest.TestSuite):
                _flatten(item)
            else:
                tests.append(item)

    _flatten(suite)

    total = len(tests)
    width = min(60, total) if total else 1

    print(f"{_Colors.BOLD}{'=' * 70}{_Colors.RESET}")
    print(f"{_Colors.BOLD}test session starts{_Colors.RESET}  "
          f"{_Colors.GREY}(file: {os.path.basename(__file__)}, {total} tests collected){_Colors.RESET}")
    print(f"{_Colors.BOLD}{'=' * 70}{_Colors.RESET}")

    result = TUITestResult()
    start = time.time()

    symbol_map = {"PASSED": (".", _Colors.GREEN), "FAILED": ("F", _Colors.RED),
                  "ERROR": ("E", _Colors.RED), "SKIPPED": ("s", _Colors.YELLOW)}

    current_class = None
    for i, test in enumerate(tests):
        cls_name = test.__class__.__name__
        if cls_name != current_class:
            if current_class is not None:
                print()
            print(f"{_Colors.CYAN}{cls_name}{_Colors.RESET}", end=" ", flush=True)
            current_class = cls_name

        test(result)
        outcome = result.results[-1][1]
        symbol, color = symbol_map[outcome]
        print(f"{color}{symbol}{_Colors.RESET}", end="", flush=True)

    elapsed = time.time() - start
    print("\n")

    failed = [r for r in result.results if r[1] in ("FAILED", "ERROR")]
    passed = [r for r in result.results if r[1] == "PASSED"]
    skipped = [r for r in result.results if r[1] == "SKIPPED"]

    if failed:
        print(f"{_Colors.BOLD}{'=' * 70}{_Colors.RESET}")
        print(f"{_Colors.BOLD}FAILURES{_Colors.RESET}")
        print(f"{_Colors.BOLD}{'=' * 70}{_Colors.RESET}")
        for test, outcome, detail in failed:
            name = f"{test.__class__.__name__}::{test._testMethodName}"
            print(f"{_Colors.RED}{_Colors.BOLD}_ {name} _{_Colors.RESET}")
            print(detail)
            print()

    print(f"{_Colors.BOLD}{'=' * 70}{_Colors.RESET}")
    summary_parts = []
    if passed:
        summary_parts.append(f"{_Colors.GREEN}{len(passed)} passed{_Colors.RESET}")
    if failed:
        summary_parts.append(f"{_Colors.RED}{len(failed)} failed{_Colors.RESET}")
    if skipped:
        summary_parts.append(f"{_Colors.YELLOW}{len(skipped)} skipped{_Colors.RESET}")
    summary = ", ".join(summary_parts) if summary_parts else "no tests ran"

    status_color = _Colors.RED if failed else _Colors.GREEN
    status_word = "FAILED" if failed else "PASSED"
    print(f"{status_color}{_Colors.BOLD}{status_word}{_Colors.RESET}  "
          f"{summary} {_Colors.GREY}in {elapsed:.2f}s{_Colors.RESET}")
    print(f"{_Colors.BOLD}{'=' * 70}{_Colors.RESET}")

    logging.disable(logging.NOTSET)
    return 0 if not failed else 1


if __name__ == "__main__":
    if "--plain" in sys.argv or "-v" in sys.argv:
        # Fallback to classic unittest verbose output:
        #   python test_ec2_controller.py --plain
        unittest.main(verbosity=2, argv=[a for a in sys.argv if a != "--plain"])
    else:
        sys.exit(run_tui())