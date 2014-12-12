#!/bin/env python

import tarfile
import traceback
import sys

###################################################################
# Feed out info
#

verbose = False

ftypes = {
    tarfile.REGTYPE: "REG",
    tarfile.AREGTYPE: "AREG",
    tarfile.LNKTYPE: "LNK",
    tarfile.SYMTYPE: "SYM",
    tarfile.CHRTYPE: "CHR",
    tarfile.BLKTYPE: "BLK",
    tarfile.DIRTYPE: "DIR",
    tarfile.FIFOTYPE: "FIFO",
    tarfile.CONTTYPE: "CONT",
    tarfile.GNUTYPE_LONGNAME: "GNULONGNAME",
    tarfile.GNUTYPE_LONGLINK: "GNULONGLINK",
    tarfile.GNUTYPE_SPARSE: "GNUSPARSE"
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

###################################################################

#
# the trick here is to check whether the member we're looking at
# is still good before we attempt to write it out
# We return the file if this is a regular file, otherwise the 
# tinfo we got is enough
#
def extract(srctar, tinfo):
    if not tinfo.isfile(): return None

    f = srctar.extractfile(tinfo)
    f.seek(-1, 2)
    try: c = f.read(1)
    except:
        sys.stderr.write("Error seeking {}\n".format(tinfo.name))
        traceback.print_exc()
        raise ValueError("Bad File: {tinfo.name}, {tinfo.size}".
                         format(tinfo=tinfo))

    p = f.tell()
    if p != tinfo.size:
        raise ValueError("File truncated: {tinfo.name}, {tinfo.size}, {size}".
                         format(tinfo=tinfo, size=p))
    f.seek(0)
    return f

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

##############################################################
#
# Command line wrapper
#

def args():
    import argparse
    global verbose

    parser = argparse.ArgumentParser()
    parser.add_argument('-v',  help="be verbose", action='store_true')
    parser.add_argument('src', help="input tar name, ending with .tar{,.gz}")
    parser.add_argument('trg', help="output tar name, ending with .tar{,.gz}")
    args = parser.parse_args()

    verbose = args.v
    return args.src, args.trg

def main():
    src, trg = args()
    srcmode, trgmode = '', ''
    for mode in 'gz',: # bz2 doesn't work
        if src.endswith('.{}'.format(mode)): srcmode = mode
        if trg.endswith('.{}'.format(mode)): trgmode = mode
    convert(src, trg, srcmode, trgmode)

if __name__ == "__main__": main()
