
%define _docdir_fmt aws-lc

%{!?make_verbose: %define make_verbose 0}
%{!?_rpmmacrodir: %global _rpmmacrodir /usr/lib/rpm/macros.d}
%{!?__cmake: %global __cmake cmake}

%undefine __cmake_in_source_build

%global source_date_epoch_from_changelog 0

%global awslc_ver_maj 1
%global awslc_ver_min 73
%global awslc_ver_patch 0
%global awslc_prefix awslc_%{awslc_ver_maj}_%{awslc_ver_min}_%{awslc_ver_patch}_

Name: aws-lc
Version: %{awslc_ver_maj}.%{awslc_ver_min}.%{awslc_ver_patch}
Release: 4%{?dist}
Summary: AWS-LC cryptographic library
License: Apache-2.0 OR ISC OR BSD-3-Clause OR MIT OR CC0-1.0 OR OpenSSL OR SSLeay-standalone
URL: https://github.com/aws/aws-lc

# TODO [childw]: use LTS FIPS release on 2025 branch
Source0: https://github.com/aws/aws-lc/archive/refs/tags/v%{version}.tar.gz#/aws-lc-%{version}.tar.gz

Patch0: aws-lc-1.73.0-dynamic-loading-test-path.patch

BuildRequires: cmake >= 3.0
BuildRequires: gcc
BuildRequires: gcc-c++
BuildRequires: golang
BuildRequires: perl-interpreter

# We use git style patches
BuildRequires: git

%description
AWS-LC is a general-purpose cryptographic library maintained by the
AWS Cryptography team for AWS and their customers. It іs based on code
from the Google BoringSSL project and the OpenSSL project.

%prep
%autosetup -n aws-lc-%{version} -S git -p1

%build
# FIPS module boundary detection requires LTO to be disabled
%define _lto_cflags %{nil}

# Build static libs first to generate the prefix symbols list
mkdir -p _symbols_build
CFLAGS="" CXXFLAGS="" %{__cmake} -S . -B _symbols_build \
    -DCMAKE_BUILD_TYPE=Release \
    -DFIPS=1 \
    -DBUILD_SHARED_LIBS=0 \
    -DBUILD_TESTING=0 \
    -DDISABLE_GO=0 \
    -DDISABLE_PERL=0
%{__cmake} --build _symbols_build --target crypto ssl -j$(nproc)
go run util/read_symbols.go _symbols_build/crypto/libcrypto.a > _symbols.txt.tmp
go run util/read_symbols.go _symbols_build/ssl/libssl.a >> _symbols.txt.tmp
# Exclude linker-defined FIPS boundary symbols that cannot be prefixed
sort -u _symbols.txt.tmp | grep -v '^BORINGSSL_bcm_' > _symbols.txt
rm -rf _symbols_build _symbols.txt.tmp

%cmake \
    -DCMAKE_VERBOSE_MAKEFILE=OFF \
    -DCMAKE_BUILD_TYPE=Release \
    -DFIPS=1 \
    -DBUILD_SHARED_LIBS=1 \
    -DENABLE_PRE_SONAME_BUILD=0 \
    -DENABLE_DIST_PKG=1 \
    -DENABLE_DIST_PKG_OPENSSL_SHIM=0 \
    -DDISABLE_GO=0 \
    -DDISABLE_PERL=0 \
    -DBUILD_TESTING=1 \
    -DBORINGSSL_PREFIX=%{awslc_prefix} \
    -DBORINGSSL_PREFIX_SYMBOLS=$(pwd)/_symbols.txt \
    -DCMAKE_SHARED_LINKER_FLAGS='-Wl,-rpath,$ORIGIN' \
    -DCMAKE_EXE_LINKER_FLAGS='-Wl,-rpath,$ORIGIN/../%{_lib}'

# use --define 'make_verbose 1' to enable verbose
%(x='%{cmake_build}'; echo ${x/ --verbose})

%install
%cmake_install
rm -rf %{buildroot}%{_prefix}/%{_lib}/crypto/cmake
rm -rf %{buildroot}%{_prefix}/%{_lib}/ssl/cmake

rm -f %{buildroot}/%{_bindir}/openssl
rm -f %{buildroot}/%{_libdir}/debug%{_bindir}/openssl-1.73.0-1.aln13.x86_64.debug

mkdir -p %{buildroot}%{_rpmmacrodir}
echo '%%%(echo %{name} |tr '-' '_')_prefix %{_prefix}' \
    > %{buildroot}%{_rpmmacrodir}/macros.%{name}

mkdir -p %{buildroot}%{_libdir}/aws-lc
ln -sf %{_libdir}/libcrypto-awslc.so %{buildroot}%{_libdir}/aws-lc/libcrypto.so
ln -sf %{_libdir}/libssl-awslc.so %{buildroot}%{_libdir}/aws-lc/libssl.so

%check
export GOPATH=$(pwd)/.gopath
export GOMODCACHE=${GOPATH}/pkg/mod
# SClientTest requires network access unavailable in mock builds
export GTEST_FILTER=-SClientTest.*
go run util/all_tests.go -build-dir %{_vpath_builddir}
chmod -R u+w .gopath 2>/dev/null || true

%files
%doc README.md
%doc NOTICE
%license LICENSE

%{_bindir}/bssl
%{_bindir}/c_rehash

%package libs
Summary: AWS-LC development files from package %{name}

%description libs
AWS-LC libraries

%files libs
%{_libdir}/libcrypto-awslc.so.*
%{_libdir}/libssl-awslc.so.*

%package devel
Summary: AWS-LC development files from package %{name}
Requires: %{name}%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}

%description devel
AWS-LC development files from package %{name}.

%files devel
%{_includedir}/aws-lc/openssl
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
