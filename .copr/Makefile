# SRPM generator for Fedora COPR's "make_srpm" source build method.
#
# COPR clones this repo into a mock chroot -- running as root, with network,
# and with only "make" and "dnf" preinstalled -- and invokes:
#
#     make -f .copr/Makefile srpm outdir=<dir> spec=<path to spec>

# Ignore the spec= that COPR passes. It is the clone directory, not the spec,
# whenever the package's "Spec File" field is empty, and rpmautospec then
# guesses the spec name from the directory name. This repo has one spec.
SPEC   := aws-lc.spec
outdir ?= $(CURDIR)

# rpmautospec does not pull in the git binary, which it needs to read history.
DEPS = git-core rpm-build rpmdevtools rpmautospec

.PHONY: srpm

srpm:
	rpm -q $(DEPS) >/dev/null 2>&1 || dnf -y install $(DEPS) --setopt=install_weak_deps=False
	# COPR clones with --depth 500. A truncated history makes rpmautospec
	# compute a wrong release and exit 0 (rpmautospec#210), so deepen first.
	# Guarded: --unshallow is fatal on an already-complete repository.
	if [ -f "$$(git rev-parse --git-dir)/shallow" ]; then git fetch --unshallow; fi
	# Expand %autorelease and %autochangelog from git history, as Koji does
	# for dist-git; nothing in COPR does it for us, and the fallback macros in
	# redhat-rpm-config are stubs that yield release 1 and a placeholder
	# changelog. Same file twice means rewrite in place. Idempotent.
	rpmautospec process-distgit "$(SPEC)" "$(SPEC)"
	# Source0 is in no lookaside cache, so fetch and verify it here.
	spectool -g -S -C "$(CURDIR)" "$(SPEC)"
	sed -E 's/^SHA512 \((.*)\) = (.*)$$/\2  \1/' sources | sha512sum -c -
	rpmbuild -bs "$(SPEC)" \
	  --define "_sourcedir $(CURDIR)" \
	  --define "_srcrpmdir $(outdir)"
