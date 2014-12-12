pytar
=====

Script to fix an interrupted/truncated tar file without a full extraction

Uses tarfile (python >= 2.7) to read a tarfile member by member (also gzipped but not bz2), 
and insert it into a new tarfile (maybe gzipped). When it fails to read a file or the file is 
shorter than declared in the tar file, it closes the output file and exits.

Question: what are the tarfile internals for seeking back and forth in a tar file, either gzipped or not?
That would define the envelope of uses.

Usage:
./pytar.py [-v] [-h] <in>.tar{.gz}? <out>.tar{.gz}?

Could be loaded as a module. The entry point would be
pytar.convert(srcname, sinkname, imode='', omode='')

where imode and omode can be 'gz', srcname is the full existing name and sinkname is the full name
of the new tar file to be created (include 'gz' if it is to be gzipped). 
In that case, pytar.verbose is a global flag for stderr verbose output
