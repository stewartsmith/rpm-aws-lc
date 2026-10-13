%global awslc_ver_maj 5
%global awslc_ver_min 2
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
Release: %autorelease
Summary: AWS-LC cryptographic library
# Derived by auditing the compiled trees, not from upstream's LICENSE summary,
# which names three licenses that do not apply to what we build. OpenSSL and
# SSLeay-standalone: AWS-LC relicensed all OpenSSL-derived code to Apache-2.0,
# and the Eric Young cryptsoft lines are copyright attributions, not grants.
# CC0-1.0: the files upstream attributes it to are Apache-2.0 and ISC. MIT comes
# from third_party/fiat and BSD-3-Clause from third_party/jitterentropy; the
# public domain files are md5-x86_64.pl and poly1305_arm_asm.S.
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
# Do not add an $ORIGIN rpath here: rpm/shell expansion strips the $ORIGIN and
# check-rpaths then rejects the result. %%{_libdir} needs no rpath anyway.
# ENABLE_DIST_PKG applies the shipped symbol version scripts (crypto/*.map).
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

# HTML API reference. doc.config sets BaseDirectory to "..", so run from util/.
export GOPROXY=off
mkdir -p html-doc
(cd util && go run doc.go -config doc.config -out ../html-doc)

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

mkdir -p %{buildroot}%{_docdir}/%{name}-doc
cp -a html-doc/. %{buildroot}%{_docdir}/%{name}-doc/
install -p -m 0644 README.md %{buildroot}%{_docdir}/%{name}-doc/

%check
# Unit tests only; see the Tests section of README.md for what is left out.
export GOPATH=$(pwd)/.gopath
export GOMODCACHE=${GOPATH}/pkg/mod
export GOPROXY=off
# Otherwise shards by runtime.NumCPU(), which ignores cgroup CPU quotas.
export AWS_LC_NUM_TEST_WORKERS=%{_smp_build_ncpus}
# These five connect to amazon.com:443; SClientTest.Help and .NoConnect do not.
export GTEST_FILTER=-SClientTest.Connect:SClientTest.ConnectVerifyShowcerts:SClientTest.Cipher:SClientTest.Tls1_1:SClientTest.CipherAndTls1_1

go run util/all_tests.go -build-dir %{_vpath_builddir}

%files
# NOTICE is the Apache-2.0 4(d) attribution, so %%license rather than %%doc:
# it has to survive --excludedocs. Repeated in every installable subpackage.
%license LICENSE
%license NOTICE

%{_bindir}/aws-lc-bssl
%{_bindir}/aws-lc-c_rehash

%package libs
Summary: AWS-LC shared libraries

# Compiled into libcrypto/libssl. The other third_party/ trees are test-only.
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
%license NOTICE
%{_libdir}/libcrypto-awslc.so.*
%{_libdir}/libssl-awslc.so.*

%package devel
Summary: Development files for AWS-LC
# The .so symlinks resolve into -libs, not the base package, which is tools only.
Requires: %{name}-libs%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}

%description devel
Headers, pkg-config files and linker symlinks needed to build against AWS-LC.
Headers are installed under %{_includedir}/aws-lc so they do not collide with
the system OpenSSL headers.

%files devel
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

%package doc
Summary: API reference documentation for AWS-LC
BuildArch: noarch

%description doc
HTML reference documentation for the AWS-LC public headers, generated from the
header comments by upstream's util/doc.go. Start at
%{_docdir}/%{name}-doc/headers.html.

%files doc
%license LICENSE
%license NOTICE
# README.md is installed into this directory, not listed with %%doc, which would
# resolve to the same path and be listed twice.
%{_docdir}/%{name}-doc

%changelog
%autochangelog
