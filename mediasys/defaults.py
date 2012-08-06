
CONFIG_DEFAULTS = """\
[mediasys]
default-distro = plain
log-format = $(levelname)s: $(message)s

[conf]
user-file = .mediasys.conf
path-environment = MEDIASYS_CONF
system-file = /etc/mediasys/mediasys.conf

[any distro]
layout = mdv
type = mandriva
config-dir = /etc/mediasys

# [media]
genhdlist-cmd = genhdlist2
install-cmd = install
lzcat-cmd = /usr/bin/lzcat
info-xml-filename = info.xml.lzma
recently-removed-dir = /var/spool/mediasys/recently-removed/
metadata-dirname = media_info
lock-filename = mediasys-at-work.lock
synthesis-name = synthesis.hdlist.cz
rpmfile-fmt = %{name}-%{version}-%{release}.%{arch}.rpm
package-copy-mode = 0644
chmod-command = chmod
genhdlist-command = genhdlist2 --xml-info-filter ".lzma:lzma -0"
       --xml-info --versioned --allow-empty-media
resign-command = /usr/bin/env -i /bin/rpm --addsign
resign-command-prompt = Enter pass phrase:
resign-signature = gpg
resign-gpg-name = Your Name Here (No comments) <youremailhere@example.com>
resign-gpg-path = ~/.gnupg
resign-passphrase-file = ~/.rpm-sign-passphrase
smartcheck-dir = /var/tmp/mediasys/smartcheck/
smartcheck-datadir = datadirs/
smartcheck-temp-media-dir = temp-medias/
smart-command = smart
smart-options = --yes -o sync-urpmi-medialist=no
debug-group-re = Development/Debug
debug-name-re = (-debug$|-debuginfo$|^kernel-.*-debug)
debug-target-media = (.*) debug_\\\\1
copy-command = cp --reflink=auto

[layout plain]
install-filters = older
medias = main
default-media = main
media main = default

[any layout]
default-media = no default media set on config
directory-structure = root package

install-filters =
move-filters =

[layout mdv]

directory-structure = root arch media package

arches = i586 x86_64 armv7hl
arch i586 = required
arch x86_64 = required

medias = main/release main/testing main/backports main/updates
    contrib/release contrib/testing contrib/backports contrib/updates
    non-free/release non-free/testing non-free/backports non-free/updates
   
   debug_main/release debug_main/testing debug_main/backports
   debug_main/updates debug_contrib/release debug_contrib/testing
   debug_contrib/backports debug_contrib/updates debug_non-free/release
   debug_non-free/testing debug_non-free/backports debug_non-free/updates

media .* = basedir=media/
media [^/]+/release = release uses=updates
media [^/]+/testing = testing uses=release,updates
media [^/]+/updates = release uses=release
media [^/]+/backports = release uses=release,updates
media main/.* = packagelist=main.pkglist section=main main
media contrib/release = default
media contrib/.* = packagelist=contrib.pkglist section=contrib
        uses-sections=main
media non-free/.* = packagelist=non-free.pkglist section=non-free
        uses-sections=main,contrib

install-filters =
    default-media
    package-list
    required-arch
    older
    sign
    debug
    release

move-filters =
    debug

[distro plain]
layout = plain
root = should come from the command line
"""
