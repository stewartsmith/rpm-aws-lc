# SRPM generator for Fedora COPR's "make_srpm" source build method.
#
# COPR clones this repo into a mock chroot (network available, running as
# root) and invokes:
#
#     make -f .copr/Makefile srpm outdir=<dir> spec=<path to spec>
#
# The upstream tarball is not committed, so fetch it here from the Source0
# URL and check it against the SHA512 manifest in ./sources.

spec ?= aws-lc.spec
outdir ?= $(CURDIR)

.PHONY: srpm

srpm:
	# rpmautospec is required, not optional: the spec uses both %autorelease
	# and %autochangelog, and an unexpanded %autorelease is not a valid Release.
	dnf -y install rpmdevtools rpm-build rpmautospec-rpm-macros
	# rpmautospec looks for a file named "changelog".
	ln -sfn amzn-changelog changelog
	spectool -g -S $(spec)
	sed -E 's/^SHA512 \((.*)\) = (.*)$$/\2  \1/' sources | sha512sum -c -
	rpmbuild -bs $(spec) \
	  --define "_sourcedir $(CURDIR)" \
	  --define "_srcrpmdir $(outdir)"
