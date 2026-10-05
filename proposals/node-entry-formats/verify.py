"""Static proposal prototype; never installs or executes an upstream SDK.

Usage: python verify.py /path/to/chain-love /path/to/json-tools
Fixtures were extracted from integrity-verified published npm archives.
"""
import copy
import base64
import csv
import hashlib
import importlib.util
import io
import json
import pathlib
import sys
import tarfile
import urllib.parse

from jsonschema import Draft202012Validator

HERE = pathlib.Path(__file__).parent
FIELD = "nodeModuleFormats"
SCHEMA = json.loads((HERE / "schema.json").read_text())
FIXTURES = json.loads((HERE / "fixtures.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def native_formats(fixture):
    found = set()
    for entry in fixture["entry_evidence"]:
        suffix = pathlib.PurePosixPath(entry["path"]).suffix
        scope_type = entry["declared_type"]
        if suffix == ".mjs" or (suffix == ".js" and scope_type == "module"):
            found.add("ESM")
        elif suffix == ".cjs" or (suffix == ".js" and scope_type == "commonjs"):
            found.add("CommonJS")
        else:
            raise ValueError("Unverified native format; do not infer from a condition name")
    return [name for name in ["ESM", "CommonJS"] if name in found]


def value_for(fixture):
    return {key: fixture[key] for key in ["package", "version", "source", "formats"]}


def semantic_check(value, fixture):
    VALIDATOR.validate(value)
    if value is None:
        return
    uri = urllib.parse.urlparse(value["source"])
    expected_path = "/" + value["package"] + "/" + value["version"]
    if (
        uri.scheme != "https"
        or uri.netloc != "registry.npmjs.org"
        or urllib.parse.unquote(uri.path) != expected_path
        or uri.query
        or uri.fragment
    ):
        raise ValueError("Source is not the matching version-specific registry manifest")
    if (value["package"], value["version"]) != (
        fixture["manifest"]["name"], fixture["manifest"]["version"]
    ):
        raise ValueError("Package/version does not match published evidence")
    if value["formats"] != native_formats(fixture):
        raise ValueError("Format list does not match verified entry files and package scopes")


def expect_rejected(value, fixture):
    try:
        semantic_check(value, fixture)
    except Exception:
        return
    raise AssertionError("Malformed or unsupported value unexpectedly accepted")


def main():
    repository = pathlib.Path(sys.argv[1])
    tooling = pathlib.Path(sys.argv[2])
    spec = importlib.util.spec_from_file_location("official_converter", tooling / "csv_to_json.py")
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    if len(sys.argv) > 3:
        archive_directory = pathlib.Path(sys.argv[3])
        for fixture in FIXTURES:
            archive = archive_directory / fixture["archive"]["filename"]
            integrity = "sha512-" + base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode()
            assert integrity == fixture["archive"]["integrity"]
            with tarfile.open(archive) as handle:
                manifest = json.loads(handle.extractfile("package/package.json").read())
                assert (manifest["name"], manifest["version"]) == (fixture["package"], fixture["version"])
                for entry in fixture["entry_evidence"]:
                    target = "package/" + entry["path"].removeprefix("./")
                    declared = manifest["exports"]["."][entry["condition"]]
                    assert declared == entry["path"]
                    content = handle.extractfile(target).read()
                    assert hashlib.sha256(content).hexdigest() == entry["sha256"]
                    scope = json.loads(handle.extractfile(entry["package_scope"]).read())
                    assert scope.get("type") == entry["declared_type"]
    for fixture in FIXTURES:
        semantic_check(value_for(fixture), fixture)
    semantic_check(None, FIXTURES[0])

    valid = value_for(FIXTURES[0])
    invalid = [
        {}, [], "ESM", {**valid, "formats": []},
        {**valid, "formats": ["ESM", "ESM"]},
        {**valid, "formats": ["esm"]},
        {**valid, "formats": ["UMD"]},
        {**valid, "formats": [False]},
        {**valid, "formats": ["CommonJS", "ESM"]},
        {**valid, "unexpected": True}, {**valid, "version": "latest"},
        {**valid, "package": "different-sdk"},
        {**valid, "source": "https://registry.npmjs.org/ethers/latest"},
        {**valid, "source": valid["source"] + "?tag=latest"},
        {**valid, "source": "https://example.org/ethers/6.17.0"},
        {**valid, "formats": ["ESM"]},
    ]
    for value in invalid:
        expect_rejected(value, FIXTURES[0])
    unclassified = copy.deepcopy(FIXTURES[0])
    unclassified["entry_evidence"][0]["declared_type"] = None
    expect_rejected(valid, unclassified)

    raw = list(csv.DictReader((repository / "references/offers/sdks.csv").open()))
    rows, errors = converter.normalize({"sdks": raw})
    assert not errors
    original = json.loads((tooling / "schema.json").read_text())["$defs"]["sdks"]
    extended = copy.deepcopy(original)
    extended["properties"][FIELD] = SCHEMA
    for row in rows["sdks"]:
        Draft202012Validator(extended).validate(row)

    selected = []
    for fixture in FIXTURES:
        row = copy.deepcopy(next(r for r in rows["sdks"] if r["slug"] == fixture["offer"]))
        row[FIELD] = value_for(fixture)
        expect_original_rejection = list(Draft202012Validator(original).iter_errors(row))
        assert expect_original_rejection
        Draft202012Validator(extended).validate(row)
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=["slug", FIELD])
        writer.writeheader()
        writer.writerow({"slug": row["slug"], FIELD: json.dumps(row[FIELD])})
        stream.seek(0)
        decoded, errors = converter.normalize({"sdks": list(csv.DictReader(stream))})
        assert not errors and decoded["sdks"][0][FIELD] == row[FIELD]
        listings, errors = converter.normalize({"sdks": [{"slug": row["slug"], "offer": "!offer:" + row["slug"], FIELD: ""}]})
        assert not errors
        inherited = converter.resolve_offers(listings, {"sdks": [row]}, "filecoin")
        assert inherited["sdks"][0][FIELD] == row[FIELD]
        selected.append(row["slug"])
    print(json.dumps({"fixtures": selected, "shape_and_semantic_rejections": len(invalid) + 1,
                      "unchanged_sdk_rows_valid": len(rows["sdks"]), "csv_roundtrip": "passed",
                      "normalization_and_inheritance": "passed", "extended_schema": "passed",
                      "archive_integrity_and_exact_entry_files": "passed" if len(sys.argv) > 3 else "not requested",
                      "upstream_sdk_execution": False}, indent=2))


if __name__ == "__main__":
    main()
