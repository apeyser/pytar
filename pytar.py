#!/bin/env python

import tarfile
import traceback
import sys

from itertools import chain
from contextlib import closing

###################################################################
# Feed out info
#

verbose = False

ftypes = {
    tarfile.REGTYPE:  "REG",
    tarfile.AREGTYPE: "AREG",
    tarfile.LNKTYPE:  "LNK",
    tarfile.SYMTYPE:  "SYM",
    tarfile.CHRTYPE:  "CHR",
    tarfile.BLKTYPE:  "BLK",
    tarfile.DIRTYPE:  "DIR",
    tarfile.FIFOTYPE: "FIFO",
    tarfile.CONTTYPE: "CONT",
    tarfile.GNUTYPE_LONGNAME: "GNULONGNAME",
    tarfile.GNUTYPE_LONGLINK: "GNULONGLINK",
    tarfile.GNUTYPE_SPARSE:   "GNUSPARSE"
}

def verboseInfo(tinfo):
    if not verbose: return

    ftype = ftypes[tinfo.type]
    if tinfo.issym() or tinfo.islnk():
        ftype = "{}: {}".format(ftype, tinfo.linkname)

    sys.stderr.write("'{tinfo.name}' "
                     "'{tinfo.size}' "
                     "'{tinfo.mtime}' "
                     "'{tinfo.mode}' "
                     "'{type}' "
                     "'{tinfo.uid}' "
                     "'{tinfo.gid}' "
                     "'{tinfo.gname}'\n".
                     format(tinfo=tinfo, type=ftype))

def verboseConvert(srcname, sinkname, imode, omode):
    if not verbose: return

    sys.stderr.write("{} ({}) -> {} ({})\n".
                     format(srcname, imode, sinkname,  omode))

def verboseConverted(srcname, sinkname, imode, omode, complete):
    if not verbose: return

    s = "Completed" if complete else "Incomplete"
    sys.stderr.write("{}: {} ({}) -> {} ({})\n".
                     format(s, srcname, imode, sinkname,  omode))

def verboseCheck(srcname, mode):
    if not verbose: return

    sys.stderr.write("Check: {} ({})\n".
                     format(srcname, mode))
    


###################################################################
#
# the trick here is to check whether the member we're looking at
# is still good before we attempt to write it out
# We return the file if this is a regular file, otherwise the 
# tinfo we got is enough
#
def extract(srctar, tinfo):
    if not tinfo.isfile(): return None

    try:
        f = srctar.extractfile(tinfo)
        # Go to the end -1 --- but this may not happen yet for gz
        f.seek(-1, 2)
        try: f.read(1) # So we try to read that last character
        except:
            sys.stderr.write("Error seeking {}\n".format(tinfo.name))
            traceback.print_exc()
            raise ValueError("Bad File: {tinfo.name}, {tinfo.size}".
                             format(tinfo=tinfo))

        # But for not gzipped files, that works but the pos is wrong
        p = f.tell()
        if p != tinfo.size:
            raise ValueError("File truncated: {tinfo.name}, {tinfo.size}".
                             format(tinfo=tinfo))
        f.seek(0)
        return f
    except: f.close(); raise

#
# Like extract, but just do the check
# Much slower than simply running tar t...
#
def checkinfo(tar, tinfo):
    if not tinfo.isfile(): return

    with closing(tar.extractfile(tinfo)) as f:
        f.seek(-1, 2)
        try: f.read(1)
        except:
            sys.stderr.write("Error seeking {}\n".format(tinfo.name))
            traceback.print_exc()
            raise ValueError("Bad File: {tinfo.name}, {tinfo.size}".
                             format(tinfo=tinfo))
        p = f.tell()
        if p != tinfo.size:
            raise ValueError("File truncated: {tinfo.name}, {tinfo.size}".
                             format(tinfo=tinfo))

#
# So in the transfer, if the extract fails to get to the end
# we bail and stopping updating the output tar
#
# Return: false if we bailed partway through
# srctar & sinktar: tarfile objects
#
def transfer(srctar, sinktar):
    for tinfo in srctar:
        verboseInfo(tinfo)
        try: f = extract(srctar, tinfo)
        except:
            sys.stderr.write("Error extracting {}\n".format(tinfo.name))
            traceback.print_exc()
            return False # Bail! Bail!

        # No exception? We should be safe to copy
        sinktar.addfile(tinfo, f)
        if f is not None: f.close()

    return True

#
# Like transfer, but just do the check on the source
# Much slower than tar t...
def checkfile(tar):
    for tinfo in tar:
        verboseInfo(tinfo)
        try: checkinfo(tar, tinfo)
        except:
            sys.stderr.write("Error checking {}\n".format(tinfo.name))
            traceback.print_exc()
            return False

#############################
# convert:
# Here's the entry point
# srcname and sinkname are file names,
# imode and omode are '' or 'gz' (bz2 doesn't work)
#
def convert(srcname, sinkname, imode='', omode=''):
    verboseConvert(srcname, sinkname, imode, omode)
    with tarfile.open(srcname, mode="r:{}".format(imode)) \
         as srctar:
        with tarfile.open(sinkname, mode="w:{}".format(omode)) \
             as sinktar:
            c = transfer(srctar, sinktar)
    verboseConverted(srcname, sinkname, imode, omode, c)

#
# Like convert, but just do the check on source
# Much slower than tar t...
def check(srcname, mode=''):
    verboseCheck(srcname, mode)
    with tarfile.open(srcname, mode='r|{}'.format(mode)) as tar:
        checkfile(tar)

##############################################################
#
# Command line wrapper
#

# convert src trg
def main_convert(src, trg):
    srcmode, trgmode = '', ''
    for mode in 'gz',: # bz2 doesn't work
        if src.endswith('.{}'.format(mode)): srcmode = mode
        if trg.endswith('.{}'.format(mode)): trgmode = mode
    convert(src, trg, srcmode, trgmode)

# check src
# Like convert, but just do the check
# Guess what? Much slower than tar t...
def main_check(src):
    srcmode = ''
    for mode in 'gz': # bz2 doesn't work
        if src.endswith('.{}'.format(mode)): srcmode = mode
    check(src, srcmode)

# arg wrapper
def main():
    import argparse
    global verbose

    parser = argparse.ArgumentParser(
        description="Some utilities for broken tar files"
    )
    parser.add_argument('-v',  help="be verbose", action='store_true')

    # Either convert or check
    # Set func to call as default value for func for sub parser
    sub = parser.add_subparsers()

    # convert
    trans = sub.add_parser("convert",
                           help='safely convert broken tar',
                           description="Read a tar file into another. "
                                       "Stops when it fails with a file, "
                                       "allowing a 'good' "
                                       "partial tar file to be created.")
    trans.add_argument('src', help="input tar name, ending with .tar{,.gz}")
    trans.add_argument('trg', help="output tar name, ending with .tar{,.gz}")
    trans.set_defaults(func=lambda: main_convert(args.src, args.trg))
    
    # check
    chk = sub.add_parser("check",
                         help='Check whether tar is broken',
                         description="Check files from beginning, stop with failure")
    chk.add_argument('src', help="input tar name, ending with .tar{,.gz}")
    chk.set_defaults(func=lambda: main_check(args.src))

    # Parse args, set verbose and call mode
    args = parser.parse_args()
    verbose = args.v
    args.func()

###################################
if __name__ == "__main__": main()
###################################
