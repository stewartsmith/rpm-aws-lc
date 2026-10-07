# aws-lc

RPM packaging for [AWS-LC](https://github.com/aws/aws-lc), a general-purpose
cryptographic library maintained by the AWS Cryptography team and derived from
Google's BoringSSL and OpenSSL.

This repository holds the spec file, patches, and source manifest only; the
upstream tarball is fetched rather than committed.

## Layout

| Path | Purpose |
| --- | --- |
| `aws-lc.spec` | Package definition |
| `sources` | SHA512 manifest of the upstream tarball |
| `*.patch` | Downstream patches, applied in spec order |
| `amzn-changelog` | Changelog entries consumed by `%autochangelog` |

## Packages

- `aws-lc` — `aws-lc-bssl` and `aws-lc-c_rehash` tools
- `aws-lc-libs` — `libcrypto-awslc.so` and `libssl-awslc.so`
- `aws-lc-devel` — headers, pkg-config files, and linker symlinks

Libraries and headers are name-suffixed and installed under `aws-lc/`, so the
package coexists with the system OpenSSL instead of replacing it. The build
enables FIPS mode and runs the upstream test suite in `%check`.

## Building

```sh
spectool -g aws-lc.spec    # fetch the tarball listed in sources
rpmbuild -ba aws-lc.spec
```
