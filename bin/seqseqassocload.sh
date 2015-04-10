#!/bin/sh
#
#  seqseqassocload.sh
###########################################################################
#
#  Purpose:  This script controls the execution of the Sequence-
#		Sequence Association loads            
#
  Usage="Usage: seqseqassocload.sh config_file"
#
#     e.g. "seqseqassocload.sh vegaprotein_seqseqassocload.config
#
#  Env Vars:
#
#      See the configuration file
#
#  Inputs:
#
#      - Common configuration file -
#		/usr/local/mgi/live/mgiconfig/master.config.sh
#      - Common load configuration file - common.config
#      - Specific load configuration file - 
#		e.g. vegaprotein_seqseqassocload.config
#      - association input file 
#
#  Outputs:
#
#      - An archive file
#      - Log files defined by the environment variables ${LOG_PROC},
#        ${LOG_DIAG}, ${LOG_CUR} and ${LOG_VAL}
#      - BCP files for for inserts to SEQ_Sequence_Assoc table
#      - Records written to the database tables
#      - Exceptions written to standard error
#      - Configuration and initialization errors are written to a log file
#        for the shell script
#
#  Exit Codes:
#
#      0:  Successful completion
#      1:  Fatal error occurred
#      2:  Non-fatal error occurred
#
#  Assumes:  Nothing
#
#  Implementation:  
#
#  Notes:  None
#
###########################################################################

#
#  Set up a log file for the shell script in case there is an error
#  during configuration and initialization.
#

cd `dirname $0`/..
LOG=`pwd`/seqseqassocload.log
rm -f ${LOG}

#
#  Verify the argument(s) to the shell script.
#
if [ $# -ne 1 ]
then
    echo ${Usage} | tee -a ${LOG}
    exit 1
fi

#
# Globals
#
TABLE=SEQ_Sequence_Assoc
COLDELIM="\t"
LINEDELIM="\n"

export TABLE COLDELIM LINEDELIM

#
#  Establish the configuration file names.
#
CONFIG_LOAD=`pwd`/$1
CONFIG_LOAD_COMMON=`pwd`/common.config

#
#  Make sure the configuration files are readable
#

if [ ! -r ${CONFIG_LOAD} ]
then
    echo "Cannot read configuration file: ${CONFIG_LOAD}"
    exit 1
fi

if [ ! -r ${CONFIG_LOAD_COMMON} ]
then
    echo "Cannot read configuration file: ${CONFIG_LOAD_COMMON}"
    exit 1
fi

#
# source config files - order is important
#
. ${CONFIG_LOAD_COMMON}
. ${CONFIG_LOAD}
#
#  Source the DLA library functions.
#
if [ "${DLAJOBSTREAMFUNC}" != "" ]
then
    if [ -r ${DLAJOBSTREAMFUNC} ]
    then
        . ${DLAJOBSTREAMFUNC}
    else
        echo "Cannot source DLA functions script: ${DLAJOBSTREAMFUNC}"
        exit 1
    fi
else
    echo "Environment variable DLAJOBSTREAMFUNC has not been defined."
    exit 1
fi

#
# check that INFILE_NAME has been set and exists
#
if [ "${INFILE_NAME}" = "" ]
then
     # set STAT for endJobStream.py called from postload in shutDown
    STAT=1
    checkStatus ${STAT} "INFILE_NAME not defined"
fi

if [ ! -r ${INFILE_NAME} ]
then
    # set STAT for endJobStream.py called from postload in shutDown
    STAT=1
    checkStatus ${STAT} "Input file: ${INFILE_NAME} does not exist"
fi

##################################################################
##################################################################
#
# main
#
##################################################################
##################################################################

#
# createArchive including OUTPUTDIR, startLog, getConfigEnv, get job key
#

preload ${OUTPUTDIR}

#
# rm files and dirs from OUTPUTDIR and RPTDIR
#

cleanDir ${OUTPUTDIR} ${RPTDIR}

#
# Create the Sequence-Sequence Association Load bcp file 
# and delete old associations
#

echo "" | tee -a ${LOG_DIAG} 
echo "`date`" | tee -a ${LOG_DIAG} 
echo "" >> ${LOG_PROC}
echo "`date`" >> ${LOG_PROC}
configName=`basename  ${CONFIG_LOAD}`
echo "Running seqseqassocload ${configName}." | tee -a ${LOG_DIAG} ${LOG_PROC}

# run the load
${SEQSEQASSOCLOAD}/bin/seqseqassocload.py >>  ${LOG_DIAG} 2>&1
STAT=$?
checkStatus ${STAT} "creating bcp file"

# bcp in
echo "" | tee -a ${LOG_DIAG}
echo "`date`" | tee -a ${LOG_DIAG}
echo "" >> ${LOG_PROC}
echo "`date`" >> ${LOG_PROC}
${PG_DBUTILS}/bin/bcpin.csh ${PG_DBSERVER} ${PG_DBNAME} ${TABLE} ${OUTPUTDIR} ${TABLE}.bcp ${COLDELIM} ${LINEDELIM} mgd >> ${LOG_DIAG} 2>&1
STAT=$?
checkStatus ${STAT} "bcp in"

#
# run postload cleanup and email logs
#
shutDown

exit 0

