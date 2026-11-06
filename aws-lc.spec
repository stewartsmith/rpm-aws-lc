%global awslc_ver_maj 5
%global awslc_ver_min 12
%global awslc_ver_patch 0

# util/fipstools/acvp/modulewrapper/main.cc #errors on any other target, so
# s390x, riscv64, i686 and loongarch64 must build with FIPS disabled.
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
Release: 1%{?dist}
Summary: AWS-LC cryptographic library
License: Apache-2.0 OR ISC OR BSD-3-Clause OR MIT OR CC0-1.0 OR OpenSSL OR SSLeay-standalone
URL: https://github.com/aws/aws-lc

Source0: https://github.com/aws/aws-lc/archive/refs/tags/v%{version}.tar.gz#/aws-lc-%{version}.tar.gz
Source1: aws-lc-provider.cnf

# Accept the "PROFILE=SYSTEM" (crypto-policies) cipher string by mapping
# it to AWS-LC's default cipher list instead of returning an error.
# Drop once AWS-LC gains real system crypto policy support upstream.
Patch: aws-lc-5.2.0-profile-system-cipher-string.patch
# Search path for aws-lc-sys (Rust) system-library auto-detection; the
# directory holds only AWS-LC symlinks so it cannot resolve to OpenSSL.
Patch: aws-lc-5.11.0-pkgconfig-awslc-libdir.patch
Patch: aws-lc-5.12.0-rehash.patch

BuildRequires: cmake >= 3.0
BuildRequires: gcc
BuildRequires: gcc-c++
BuildRequires: clang
BuildRequires: golang
BuildRequires: perl-interpreter
BuildRequires: bindgen-cli

# We use git style patches
BuildRequires: git
Requires: %{name}-libs%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}

%description
AWS-LC is a general-purpose cryptographic library maintained by the
AWS Cryptography team for AWS and their customers. It is based on code
from the Google BoringSSL project and the OpenSSL project.

%prep
%autosetup -n aws-lc-%{version} -S git -p1

%build
# Do not add an $ORIGIN rpath here: the libraries install into %%{_libdir},
# which needs no rpath, and $ORIGIN does not survive to the linker intact, so
# check-rpaths rejects the result.
#
# ENABLE_DIST_PKG applies AWS-LC's shipped symbol version scripts
# (crypto/libcrypto.map, ssl/libssl.map) automatically.
#
# ENABLE_CRYPTO_POLICIES seeds every SSL_CTX from the system crypto-policies
# OpenSSL back-end. The AWSLC_CRYPTO_POLICY_FILE override points AWS-LC at the
# dedicated aws-lc.config back-end that newer crypto-policies generated.
%cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DFIPS=%{awslc_fips} \
    -DBUILD_SHARED_LIBS=1 \
    -DENABLE_PRE_SONAME_BUILD=0 \
    -DENABLE_DIST_PKG=1 \
    -DENABLE_DIST_PKG_OPENSSL_SHIM=0 \
    -DENABLE_CRYPTO_POLICIES=1 \
    -DAWSLC_CRYPTO_POLICY_FILE="/etc/crypto-policies/back-ends/aws-lc.config" \
    -DDISABLE_GO=0 \
    -DDISABLE_PERL=0 \
    -DBUILD_TESTING=1 \
    -DGENERATE_RUST_BINDINGS=ON \
    -DBUILD_AWSLC_PROVIDER=ON

%cmake_build

%install
%cmake_install
# Drop upstream's CMake config files rather than relocate them to
# %%{_libdir}/cmake: they export find_package(crypto) and find_package(ssl),
# names far too generic to claim, and their install paths would have this
# package own %%{_libdir}/crypto and %%{_libdir}/ssl. Consumers use pkg-config.
rm -rf %{buildroot}%{_libdir}/crypto/cmake
rm -rf %{buildroot}%{_libdir}/ssl/cmake

mkdir -p %{buildroot}%{_libdir}/aws-lc
ln -sf %{_libdir}/libcrypto-awslc.so %{buildroot}%{_libdir}/aws-lc/libcrypto.so
ln -sf %{_libdir}/libssl-awslc.so %{buildroot}%{_libdir}/aws-lc/libssl.so

mv %{buildroot}%{_includedir}/rust_wrapper.h %{buildroot}%{_includedir}/aws-lc/

install -m 755 -d %{buildroot}%{_sysconfdir}/pki/tls/openssl.d
install -m 644 %{SOURCE1} %{buildroot}%{_sysconfdir}/pki/tls/openssl.d/aws-lc-provider.cnf

%check
export GOPATH=$(pwd)/.gopath
export GOMODCACHE=${GOPATH}/pkg/mod
# SClientTest requires network access unavailable in mock builds
export GTEST_FILTER=-SClientTest.*
# The ssl tests assert AWS-LC's built-in defaults, which the buildroot's
# crypto-policies back-end would override now that ENABLE_CRYPTO_POLICIES is
# on. Point the loader at a missing file; the crypto-policy tests supply their
# own fixtures through this same variable.
export AWSLC_CRYPTO_POLICY_FILE=%{_builddir}/no-such-opensslcnf.config
go run util/all_tests.go -build-dir %{_vpath_builddir}
chmod -R u+w .gopath 2>/dev/null || true

# Run provider tests
%{_vpath_builddir}/provider/awslc_provider_test
%{_vpath_builddir}/provider/awslc_provider_backend_test

# This Cmake target will check the linkage situation in the provider by
# making sure that all the symbols come from the libraries we expect them to.
%{__cmake} --build %{_vpath_builddir} --target awslc_provider_linkage_test

%files
%doc README.md
%doc NOTICE
%license LICENSE

%{_bindir}/aws-lc-openssl
%{_bindir}/aws-lc-bssl
%{_bindir}/aws-lc-c_rehash

%package libs
Summary: AWS-LC shared libraries
Requires: crypto-policies >= 20260811-1

%description libs
AWS-LC libraries

%files libs
%{_libdir}/libcrypto-awslc.so.*
%{_libdir}/libssl-awslc.so.*

%package devel
Summary: AWS-LC development files from package %{name}
Requires: %{name}%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires: %{name}-libs%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}

%description devel
AWS-LC development files from package %{name}.

%files devel
%dir %{_includedir}/aws-lc
%{_includedir}/aws-lc/openssl
%{_includedir}/aws-lc/rust_wrapper.h
%{_libdir}/pkgconfig/libcrypto-awslc.pc
%{_libdir}/pkgconfig/libssl-awslc.pc
%{_libdir}/pkgconfig/aws-lc.pc
%{_libdir}/libcrypto-awslc.so
%{_libdir}/libssl-awslc.so
%dir %{_libdir}/aws-lc
%{_libdir}/aws-lc/libcrypto.so
%{_libdir}/aws-lc/libssl.so
%dir %{_datadir}/rust
%{_datadir}/rust/aws_lc_bindings.rs

%package provider
Summary: AWS-LC provider for OpenSSL
BuildRequires: openssl-devel
Requires: openssl-libs
Requires: %{name}-libs%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}

%description provider
AWS-LC provider for OpenSSL

%files provider
%attr(0755,root,root) %{_libdir}/ossl-modules/awslc.so
%config(noreplace) %{_sysconfdir}/pki/tls/openssl.d/aws-lc-provider.cnf

%changelog
%autochangelog
