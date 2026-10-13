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
License: Apache-2.0 OR ISC OR BSD-3-Clause OR MIT OR CC0-1.0 OR OpenSSL OR SSLeay-standalone
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
export GOPATH=$(pwd)/.gopath
export GOMODCACHE=${GOPATH}/pkg/mod
# all_tests.go only imports stdlib and in-module packages, so module graph
# pruning keeps it offline despite the unused golang.org/x/crypto requirement
# in go.mod. Fail loudly rather than hang if that ever stops being true.
export GOPROXY=off
# SClientTest requires network access unavailable in mock builds
export GTEST_FILTER=-SClientTest.*
go run util/all_tests.go -build-dir %{_vpath_builddir}
chmod -R u+w .gopath 2>/dev/null || true

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
