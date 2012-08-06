import os
import time
import pty
import select
import logging

def run_passphrase_command(cmd, passphrase, prompt):
    pid, fd = pty.fork()
    if pid == 0:
        os.execl(cmd[0], *cmd)
    else:
        line = ""
        while prompt not in line:
            (rl, _, xl) = select.select([fd], [], [fd], 5)
            if rl:
                line = os.read(fd, 1024)
            elif xl:
                break
        os.write(fd, "%s\n" % (passphrase))
        _, status = os.waitpid(pid, 0)
        output = os.read(fd, 8196)
        return status, output

def node_dev(path):
    if not os.path.exists(path):
        path = os.path.dirname(path)
    st = os.stat(path)
    return st.st_dev

def same_partition(one, other):
    return node_dev(one) == node_dev(other)
