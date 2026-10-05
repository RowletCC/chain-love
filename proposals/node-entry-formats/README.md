# SDK native Node entry-format prototype

This supports a data-model proposal, not a catalogue migration. No SDK is installed or executed. The current offers and SDK columns remain unchanged.

Pinned input data: Chain.Love `d63e7e438588aff29c2b819ff6c34abb7ed6a0ac`. Official conversion/schema tooling: json-tools `830d5f05ae15954c43ef23f4085c83d4548d5431`.

The two existing Filecoin-listed offers have different published root-entry formats:

- `ethers-js`: ethers 6.17.0 provides an ESM `import` path under `lib.esm/package.json` with `type: module`, and a CommonJS `default` path under `lib.commonjs/package.json` with `type: commonjs`.
- `synapse-sdk`: @filoz/synapse-sdk 2.0.2 provides one compiled-JavaScript root entry under an explicit `type: module` package scope.

`fixtures.json` contains exact published manifest fragments, entry-file hashes, package scopes and npm tarball SHA-512 provenance. `schema.json` is the illustrative optional field schema. The executable prototype verifies schema/source identity, native-format evidence, CSV round-trip, the official converter's normalization and offer inheritance, and compatibility of all 203 unchanged upstream SDK rows. It rejects 17 malformed or unsupported cases.

With Python 3.12 and `jsonschema` available, run from any working directory:

```sh
python verify.py /path/to/chain-love /path/to/json-tools
```

For an independent archive check, fetch the two public tarball URLs in `fixtures.json`, save them with the given `archive.filename` values in one directory, then run:

```sh
python verify.py /path/to/chain-love /path/to/json-tools /path/to/downloaded-archives
```

The optional archive check validates npm SHA-512 integrity, exact package/version identity, exported paths, entry-file SHA-256 and controlling package types by reading archive members without extraction or code execution. The checked-in result records the run with both archives verified.

The small classifier deliberately refuses ambiguous `.js` entries without explicit package type. It does not infer ESM/CJS from condition names, file-directory names, TypeScript use, browser/Node support or successful loading. It is not a general Node resolver, export-condition solver, runtime compatibility test or production migration.

Primary definitions: [Node package scopes and file extensions](https://nodejs.org/api/packages.html#packagejson-and-file-extensions), [conditional exports](https://nodejs.org/api/packages.html#conditional-exports). Exact source manifests: [ethers 6.17.0](https://registry.npmjs.org/ethers/6.17.0), [Synapse SDK 2.0.2](https://registry.npmjs.org/@filoz/synapse-sdk/2.0.2).
