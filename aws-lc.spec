%global awslc_ver_maj 5
%global awslc_ver_min 2
%global awslc_ver_patch 0

# AWS-LC supports FIPS mode on a subset of its target architectures. The hard
# gate is the guard in util/fipstools/acvp/modulewrapper/main.cc, which only
# accepts OPENSSL_X86_64, OPENSSL_ARM, OPENSSL_AARCH64, OPENSSL_PPC64LE,
# OPENSSL_PPC32BE and OPENSSL_PPC64BE, and #errors out otherwise. Everything
# else Fedora builds for (s390x, riscv64, i686, loongarch64) must therefore
# build with FIPS disabled.
%global fips_arches x86_64 aarch64 ppc64le %{arm}

%ifarch %{fips_arches}
%global awslc_fips 1
%else
%global awslc_fips 0
%endif

%if %{awslc_fips}
# FIPS module boundary detection requires LTO to be disabled.
%global _lto_cflags %{nil}
%endif

Name: aws-lc
Version: %{awslc_ver_maj}.%{awslc_ver_min}.%{awslc_ver_patch}
Release: %autorelease
Summary: AWS-LC cryptographic library
# Upstream LICENSE is a summary and does not match the sources in two places,
# so the tag below is derived by auditing every non-test source file in the
# trees CMake actually compiles -- crypto/, ssl/, tool/, tool-openssl/,
# include/, and the third_party/ subtrees pulled in by add_subdirectory or
# #include:
#
#   crypto/, ssl/, tool/,     Apache-2.0 and ISC, plus ORs over
#   tool-openssl/, include/     Apache-2.0/ISC/MIT. Two files carry no SPDX
#                               tag and are public domain; see below.
#   third_party/s2n-bignum    ORs over Apache-2.0/ISC/MIT-0
#   third_party/fiat          MIT (no SPDX tags; see its LICENSE). Compiled in
#                               via the p256/p384/p521 and curve25519 headers.
#   third_party/jitterentropy BSD-3-Clause. Dual BSD/GPL-2.0 upstream, and
#                               Amazon expressly elects BSD. Built unless
#                               DISABLE_CPU_JITTER_ENTROPY, which we do not set.
#
# Every OR resolves to Apache-2.0 or ISC, both already required, so only MIT
# (fiat), BSD-3-Clause (jitterentropy) and the public domain files add to the
# set. The public domain code is compiled in on specific arches:
#
#   crypto/fipsmodule/md5/asm/md5-x86_64.pl  x86_64, via perlasm() in
#     crypto/fipsmodule/CMakeLists.txt. "I hereby disclaim the copyright on
#     this code and place it in the public domain."
#   crypto/poly1305/poly1305_arm_asm.S  32-bit arm, guarded by OPENSSL_ARM.
#     Taken from the public domain neon2 version in SUPERCOP.
#
# Upstream LICENSE names these, but they do not apply to what we build:
#
#   OpenSSL, SSLeay-standalone  AWS-LC relicensed all OpenSSL-derived code to
#     Apache-2.0, as its LICENSE states. No compiled source carries SPDX
#     OpenSSL, and none carries the legacy SSLeay license grant. The 188 files
#     bearing the Eric Young cryptsoft copyright are all SPDX Apache-2.0 --
#     that line is a copyright attribution to preserve, not a license grant.
#   CC0-1.0  Upstream LICENSE attributes its CC0 section to the Keccak and AES
#     reference implementations, but those are licensed otherwise:
#     keccak1600.c is Apache-2.0 and aes_nohw.c is ISC. The public domain code
#     above is a dedication rather than a CC0 grant, so Fedora's
#     LicenseRef-Fedora-Public-Domain covers it.
License: Apache-2.0 AND ISC AND MIT AND BSD-3-Clause AND LicenseRef-Fedora-Public-Domain
URL: https://github.com/aws/aws-lc

Source0: https://github.com/aws/aws-lc/archive/refs/tags/v%{version}.tar.gz#/aws-lc-%{version}.tar.gz

# Accept the "PROFILE=SYSTEM" (crypto-policies) cipher string by mapping
# it to AWS-LC's default cipher list instead of returning an error.
# Drop once AWS-LC gains real system crypto policy support upstream.
Patch: aws-lc-5.2.0-profile-system-cipher-string.patch

BuildRequires: cmake
BuildRequires: gcc
BuildRequires: gcc-c++
BuildRequires: golang
BuildRequires: perl-interpreter

# We use git style patches
BuildRequires: git-core

%description
AWS-LC is a general-purpose cryptographic library maintained by the
AWS Cryptography team for AWS and their customers. It is based on code
from the Google BoringSSL project and the OpenSSL project.

%prep
%autosetup -n aws-lc-%{version} -S git -p1

%build
# No rpath is set: the libraries install into %%{_libdir}, which is already on
# the default linker search path. An $ORIGIN-relative rpath would be stripped
# of its $ORIGIN by rpm/shell expansion and rejected by check-rpaths.
#
# ENABLE_DIST_PKG applies AWS-LC's shipped symbol version scripts
# (crypto/libcrypto.map, ssl/libssl.map) automatically.
%cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DFIPS=%{awslc_fips} \
    -DBUILD_SHARED_LIBS=1 \
    -DENABLE_PRE_SONAME_BUILD=0 \
    -DENABLE_DIST_PKG=1 \
    -DENABLE_DIST_PKG_OPENSSL_SHIM=0 \
    -DDISABLE_GO=0 \
    -DDISABLE_PERL=0 \
    -DBUILD_TESTING=1

%cmake_build

%install
%cmake_install
rm -rf %{buildroot}%{_libdir}/crypto/cmake
rm -rf %{buildroot}%{_libdir}/ssl/cmake

rm -f %{buildroot}%{_bindir}/aws-lc-openssl

mkdir -p %{buildroot}%{_rpmmacrodir}
echo '%%%(echo %{name} |tr '-' '_')_prefix %{_prefix}' \
    > %{buildroot}%{_rpmmacrodir}/macros.%{name}

mkdir -p %{buildroot}%{_libdir}/aws-lc
ln -sf %{_libdir}/libcrypto-awslc.so %{buildroot}%{_libdir}/aws-lc/libcrypto.so
ln -sf %{_libdir}/libssl-awslc.so %{buildroot}%{_libdir}/aws-lc/libssl.so

%check
# This runs upstream's unit tests only: 27 invocations across crypto_test,
# ssl_test, tool_openssl_test and the isolated mem/rand/rwlock binaries. The
# other two legs of upstream's run_tests target are not run, because both need
# golang.org/x/crypto and there is no vendor directory to satisfy it offline:
# the ssl/test/runner TLS suite (a fork of Go's crypto/tls that handshakes
# against libssl through bssl_shim) and, under FIPS, the ACVP tests.
export GOPATH=$(pwd)/.gopath
export GOMODCACHE=${GOPATH}/pkg/mod
# all_tests.go imports only stdlib and in-module packages, so module graph
# pruning keeps it offline. Fail loudly rather than hang if that ever changes.
export GOPROXY=off

# all_tests.go otherwise shards crypto_test runtime.NumCPU() ways, which
# ignores cgroup CPU quotas and over-subscribes a constrained builder.
export AWS_LC_NUM_TEST_WORKERS=%{_smp_build_ncpus}

# These five SClientTest cases connect to amazon.com:443 through the s_client
# tool. SClientTest.Help and SClientTest.NoConnect do not, so they still run.
# ocsp_integration_test is the only other test doing real network I/O, and it
# is a separate binary that all_tests.json does not reference.
export GTEST_FILTER=-SClientTest.Connect:SClientTest.ConnectVerifyShowcerts:SClientTest.Cipher:SClientTest.Tls1_1:SClientTest.CipherAndTls1_1

go run util/all_tests.go -build-dir %{_vpath_builddir}

%files
%doc README.md
%doc NOTICE
%license LICENSE

%{_bindir}/aws-lc-bssl
%{_bindir}/aws-lc-c_rehash

%package libs
Summary: AWS-LC shared libraries

# Third-party code compiled into libcrypto/libssl. The googletest, wycheproof
# and vectors trees under third_party/ are test-only and are not shipped.
Provides: bundled(fiat-crypto)
Provides: bundled(jitterentropy)
Provides: bundled(mldsa-native)
Provides: bundled(mlkem-native)
Provides: bundled(s2n-bignum)

%description libs
The libcrypto-awslc and libssl-awslc shared libraries. These are name-suffixed
so they can be installed alongside the system OpenSSL rather than replacing it.

%files libs
%license LICENSE
%{_libdir}/libcrypto-awslc.so.*
%{_libdir}/libssl-awslc.so.*

%package devel
Summary: Development files for AWS-LC
# The .so symlinks here resolve into the libraries shipped by -libs, so depend
# on that rather than on the base package, which holds only the tools.
Requires: %{name}-libs%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}

%description devel
Headers, pkg-config files and linker symlinks needed to build against AWS-LC.
Headers are installed under %{_includedir}/aws-lc so they do not collide with
the system OpenSSL headers.

%files devel
# Upstream guidance for writing code against AWS-LC: PORTING.md covers moving
# from OpenSSL, API-CONVENTIONS.md the library's own conventions.
%doc API-CONVENTIONS.md
%doc PORTING.md
%{_includedir}/aws-lc/
%{_libdir}/pkgconfig/libcrypto-awslc.pc
%{_libdir}/pkgconfig/libssl-awslc.pc
%{_libdir}/pkgconfig/aws-lc.pc
%{_rpmmacrodir}/macros.%{name}
%{_libdir}/libcrypto-awslc.so
%{_libdir}/libssl-awslc.so
%dir %{_libdir}/aws-lc
%{_libdir}/aws-lc/libcrypto.so
%{_libdir}/aws-lc/libssl.so

%changelog
%autochangelog
