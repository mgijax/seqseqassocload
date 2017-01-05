#!/usr/local/bin/python

##########################################################################
#
# Purpose:
#       Load Sequence-Sequence Associations to SEQ_Sequence_Assoc
#
# Usage: seqseqassocload.py
# Env Vars:
#	 1. OUTPUTDIR
#	 2. MGD_DBSERVER
#	 3. MGD_DBNAME
#	 4. MGD_DBPASSWORDFILE
#	 5. MGD_DBUSER
#	 6. TABLE
#	 7. INFILE_NAME
#	 8. SEQ1_LOGICAL_DBKEY
#	 9. SEQ2_LOGICAL_DBKEY
#	10. USER_KEY 
#
# Inputs:
#	1. tab-delimited in following format:
#	    1. seqId1
#           2. qualifier
#           3. seqId2
#	2. Configuration 
#
# Outputs:
#	 1. SEQ_Sequence_Assoc bcp file
#	 2. log file
# 
# Exit Codes:
#
#      0:  Successful completion
#      1:  An exception occurred
#
#  Assumes:  Nothing
#
#  Notes:  None
#
###########################################################################

import sys
import os
import mgi_utils
import string
import db

#
# Constants
#
TAB= '\t'
CRT = '\n'

# Qualifier vocabulary key
QUAL_VOCAB_KEY = 78

# MGI_User key for the load
CREATEDBY_KEY = os.environ['USERKEY']

#
# GLOBALS
#

# database connection info
mgdServer = os.environ['MGD_DBSERVER']
mgdDB = os.environ['MGD_DBNAME']
passwdfile = os.environ['MGD_DBPASSWORDFILE']
password = string.strip(open(passwdfile, 'r').readline())
user = os.environ['MGD_DBUSER']

# the table we are  loading
table = os.environ['TABLE']

# timestamp for creation/modification date
cdate = mgi_utils.date('%m/%d/%Y')      # current date

# file descriptors
# input file 
inFile = ''

# bcp file
outFile = ''

# Lookup to verify seq1 sequence {seqId:seqKey, ...}
seq1Lookup = {} 

# Qualifier lookup {term:termKey, ...}
qualLookup = {}

# Lookup to verify seq2 sequence {seqId:seqKey, ...}
seq2Lookup = {}

# current available _Assoc_key
nextKey= ''

def init():
    # Purpose: initialize file descriptors, create connection to
    #  the database and load lookups
    # Returns: nothing
    # Assumes: nothing
    # Effects: gives SQL commands to the database
    # Throws: nothing
    global inFile, outFile, nextKey

    print '%s' % mgi_utils.date()
    print 'Initializing'
   
    db.useOneConnection(1)
    db.set_sqlLogin(user, password, mgdServer, mgdDB)
 
    results = db.sql('''select max(_Assoc_key) + 1 as nextKey from %s''' % table, 'auto')
    nextKey = results[0]['nextKey']
    if nextKey == None:
	nextKey = 1001

    inFilePath = os.environ['INFILE_NAME']
    try:
	inFile = open(inFilePath, 'r')
    except:
	exit('Could not open file for reading %s\n' % inFilePath)

    outFilePath = '%s/%s.bcp' % (os.environ['OUTPUTDIR'],  table)
    try:
	outFile = open(outFilePath, 'w')
    except:
        exit('Could not open file for writing %s\n' % outFilePath)

    loadLookups()

def loadLookups():
    # Purpose: loads lookups
    # Returns: nothing
    # Assumes: connection has been made to the database
    # Effects: gives SQL commands to the database
    # Throws: nothing

    global seq1Lookup, qualLookup, seq2Lookup

    seq1LdbKey = os.environ['SEQ1_LOGICAL_DBKEY']
    seq2LdbKey = os.environ['SEQ2_LOGICAL_DBKEY']
    #
    # Load seq1Lookup
    #
    results = db.sql('''select _Object_key as _Sequence_key, accID
	from ACC_Accession
	where _MGIType_key = 19 
	and preferred = 1 
	and _LogicalDB_key = %s''' % seq1LdbKey, 'auto')
    for r in results:
        seqKey = r['_Sequence_key']
        seqId = r['accID']
	seq1Lookup[seqId] = seqKey
    #
    # Load qualLookup
    #
    results = db.sql('''select _Term_key, term from VOC_Term where _Vocab_key = %s''' % QUAL_VOCAB_KEY, 'auto')
    for r in results:
	qualKey = r['_Term_key']
	qualifier = r['term']
	qualLookup[qualifier] = qualKey
    #
    # Load seq2Lookup
    #
    results = db.sql('''select _Object_key as _Sequence_key, accID 
        from ACC_Accession 
        where _MGIType_key = 19 
        and preferred = 1 
        and _LogicalDB_key = %s''' % seq2LdbKey, 'auto')
    for r in results:
        seqKey = r['_Sequence_key']
        seqId = r['accID']
        seq2Lookup[seqId] = seqKey

def deleteByUser():
    # Purpose: delete records created by current load
    # Returns: nothing
    # Assumes: a connection has been made to the database
    # Effects: deletes records from a database
    # Throws: nothing

    print '%s' % mgi_utils.date()
    print 'Deleting records for this user'
    db.sql('''delete from %s where _CreatedBy_key = %s''' % (table, CREATEDBY_KEY), None)
    db.commit()

def run():
    # Purpose: iterate through the input file, resolving to keys
    #  and writing to a bcp file
    # Returns: nothing
    # Assumes: inFile and outFile are valid file descriptors
    # Effects: writes to the file system
    # Throws: nothing

    global nextKey
    print '%s' % mgi_utils.date()
    print 'Creating bcp file'
    for line in inFile.readlines():
        (seqId1, qualifier, seqId2) = string.split(line, TAB)
	seqId1 = string.strip(seqId1)
	qualifier = string.strip(qualifier)
	seqId2 = string.strip(seqId2)
        if seq1Lookup.has_key(seqId1):
	    seqKey1 = seq1Lookup[seqId1]
	else:
	    print 'SeqId1 %s is not in the database' % seqId1
	    continue
	if qualLookup.has_key(qualifier):
	    qualKey = qualLookup[qualifier]
	else:
	    print 'Qualifier %s is not in the database' % qualifier
	    continue 
 	if seq2Lookup.has_key(seqId2):
	    seqKey2 = seq2Lookup[seqId2]
	else:
            print 'SeqId2 %s is not in the database' % seqId2
	    continue
	outFile.write('%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s' % \
	    (nextKey, TAB, seqKey1, TAB, qualKey, TAB, seqKey2, \
		TAB, CREATEDBY_KEY, TAB, CREATEDBY_KEY, TAB, cdate, TAB, cdate, CRT))
	nextKey = nextKey + 1

def finalize():
    # Purpose: closes file descriptors and connection to the db
    # Returns: nothing
    # Assumes: nothing
    # Effects: nothing
    # Throws: nothing

    global inFile, outFile
    db.useOneConnection(0)
    inFile.close()
    outFile.close()

#
# Main
#
init()
run()
deleteByUser()
finalize()

print '%s' % mgi_utils.date()
