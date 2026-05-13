
%define _docdir_fmt aws-lc

%{!?make_verbose: %define make_verbose 0}

%if 0%{?rhel} <= 8
%undefine __cmake_in_source_build
%endif

%global source_date_epoch_from_changelog 0

Name: aws-lc
Version: 1.73.0
Release: 3%{?dist}
Summary: AWS-LC cryptographic library
License: Apache-2.0 OR ISC OR BSD-3-Clause OR MIT OR CC0-1.0 OR OpenSSL OR SSLeay-standalone
URL: https://github.com/aws/aws-lc

Source0: https://github.com/aws/aws-lc/archive/refs/tags/v%{version}.tar.gz#/aws-lc-%{version}.tar.gz


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

%cmake \
    %if !%{make_verbose}
    -DCMAKE_VERBOSE_MAKEFILE=OFF \
    %endif
    -DCMAKE_BUILD_TYPE=Release \
    -DFIPS=1 \
    -DBUILD_SHARED_LIBS=1 \
    -DENABLE_PRE_SONAME_BUILD=0 \
    -DENABLE_DIST_PKG=1 \
    -DENABLE_DIST_PKG_OPENSSL_SHIM=0 \
    -DDISABLE_GO=0 \
    -DDISABLE_PERL=0 \
    -DBUILD_TESTING=0 \
    -DCMAKE_SHARED_LINKER_FLAGS='-Wl,-rpath,$ORIGIN' \
    -DCMAKE_EXE_LINKER_FLAGS='-Wl,-rpath,$ORIGIN/../%{_lib}'

# use --define 'make_verbose 1' to enable verbose
%(x='%{cmake_build}'; echo ${x/ --verbose})

%install
%cmake_install
rm -rf %{buildroot}%{_prefix}/%{_lib}/crypto/cmake
rm -rf %{buildroot}%{_prefix}/%{_lib}/ssl/cmake

mkdir -p %{buildroot}%{_rpmmacrodir}
echo '%%%(echo %{name} |tr '-' '_')_prefix %{_prefix}' \
    > %{buildroot}%{_rpmmacrodir}/macros.%{name}

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



%changelog
