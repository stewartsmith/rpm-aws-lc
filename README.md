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
runs the upstream test suite in `%check`.

## FIPS mode

FIPS mode is enabled only on the architectures AWS-LC supports it on —
`x86_64`, `aarch64`, `ppc64le`, and 32-bit arm — and disabled everywhere else.
The gate is upstream's gate: `util/fipstools/acvp/modulewrapper/main.cc` fails
the build with `#error "FIPS build not supported on this architecture"` on any
target it does not recognise, which is what `s390x`, `riscv64`, `i686`, and
`loongarch64` hit. The arch list lives in the `fips_arches` macro in the spec.

## Building

```sh
spectool -g aws-lc.spec    # fetch the tarball listed in sources
rpmbuild -ba aws-lc.spec
```

## Fedora COPR

COPR builds this repo directly via the `make_srpm` source build method; the
tarball is fetched at SRPM time by `.copr/Makefile` rather than committed.

```sh
copr-cli add-package-scm aws-lc --name aws-lc \
  --clone-url <public clone url> --commit <branch> \
  --spec aws-lc.spec --type git --method make_srpm
copr-cli build-package aws-lc --name aws-lc
```

To reproduce COPR's SRPM step locally:

```sh
make -f .copr/Makefile srpm outdir=/tmp/srpm
```
