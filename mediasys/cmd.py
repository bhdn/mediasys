#
# Copyright (c) 2012 Bogdano Arendartchuk <bogdano@mandriva.com.br>
#
# Written by Bogdano Arendartchuk <bogdano@mandriva.com.br>
#
# This file is part of Mediasys.
#
# Mediasys is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# Mediasys is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mediasys; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
import os
import subprocess
from mediasys import Error

class CommandError(Error):
    pass

def run(args, error=False):
    proc = subprocess.Popen(args=args, shell=False,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    proc.wait()
    output = proc.stdout.read()
    if proc.returncode != 0 and error:
        cmdline = subprocess.list2cmdline(args)
        raise CommandError, ("command failed: %s\n%s\n" %
                (cmdline, output))
    return output, proc.returncode
