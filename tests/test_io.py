import json
import tempfile
import unittest
from pathlib import Path

from hdp.diagnostics import HdpInputError
from hdp.io import atomic_write_text, canonical_json, load_document


class IoTests(unittest.TestCase):
    def test_yaml_uses_safe_loader(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.yaml"
            path.write_text("value: !!python/object/apply:os.system ['false']\n")
            with self.assertRaises(HdpInputError):
                load_document(path)

    def test_document_must_be_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "list.json"
            path.write_text("[]")
            with self.assertRaises(HdpInputError):
                load_document(path)

    def test_yaml_rejects_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.yaml"
            path.write_text("value: first\nvalue: second\n")
            with self.assertRaisesRegex(HdpInputError, "duplicate key"):
                load_document(path)

    def test_yaml_rejects_anchors_and_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alias.yaml"
            path.write_text("first: &shared {value: one}\nsecond: *shared\n")
            with self.assertRaisesRegex(HdpInputError, "anchors and aliases"):
                load_document(path)

    def test_yaml_rejects_merge_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "merge.yaml"
            path.write_text("value:\n  <<: {enabled: true}\n")
            with self.assertRaisesRegex(HdpInputError, "merge keys"):
                load_document(path)

    def test_yaml_rejects_non_string_mapping_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "numeric-key.yaml"
            path.write_text("1: value\n")
            with self.assertRaisesRegex(HdpInputError, "keys must be strings"):
                load_document(path)

    def test_json_rejects_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"value":"first","value":"second"}')
            with self.assertRaisesRegex(HdpInputError, "duplicate key"):
                load_document(path)

    def test_document_byte_limit_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized.json"
            path.write_text('{"value":"' + ("x" * 1_048_576) + '"}')
            with self.assertRaisesRegex(HdpInputError, "exceeds 1048576 bytes"):
                load_document(path)

    def test_document_depth_limit_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "deep.json"
            path.write_text('{"value":' * 65 + "null" + "}" * 65)
            with self.assertRaisesRegex(HdpInputError, "maximum depth 64"):
                load_document(path)

    def test_document_item_limit_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "many-items.json"
            path.write_text(json.dumps({"values": [0] * 100_001}))
            with self.assertRaisesRegex(HdpInputError, "more than 100000 items"):
                load_document(path)

    def test_canonical_json_is_order_independent(self) -> None:
        self.assertEqual(canonical_json({"b": 2, "a": 1}), '{"a":1,"b":2}')

    def test_atomic_write_replaces_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "value.json"
            atomic_write_text(path, json.dumps({"ok": True}))
            self.assertEqual(json.loads(path.read_text()), {"ok": True})


if __name__ == "__main__":
    unittest.main()
