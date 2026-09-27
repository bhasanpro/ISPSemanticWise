#!/bin/ksh
#===============================================================================
# pre_process_trades.ksh
# Pre-processing script for trade files before Ab Initio ingestion
#===============================================================================

# Set environment
export TRADE_DATE=${1:-$(date +%Y%m%d)}
export BATCH_ID=$(date +%Y%m%d%H%M%S)
export INPUT_DIR="/data/input/trades"
export OUTPUT_DIR="/data/output/trades"
export ARCHIVE_DIR="/archive/trades"
export LOG_FILE="/logs/pre_process_${TRADE_DATE}.log"

#===============================================================================
# FUNCTIONS
#===============================================================================

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a ${LOG_FILE}
}

check_file_exists() {
    if [[ ! -f $1 ]]; then
        log_message "ERROR: File not found: $1"
        return 1
    fi
    return 0
}

validate_file_format() {
    local file=$1
    local expected_cols=$2
    
    local first_line=$(head -1 ${file})
    local col_count=$(echo ${first_line} | awk -F',' '{print NF}')
    
    if [[ ${col_count} -ne ${expected_cols} ]]; then
        log_message "ERROR: Invalid column count in ${file}. Expected ${expected_cols}, got ${col_count}"
        return 1
    fi
    return 0
}

cleanup_temp_files() {
    rm -f ${OUTPUT_DIR}/*.tmp 2>/dev/null
    log_message "Cleaned up temporary files"
}

#===============================================================================
# MAIN PROCESSING
#===============================================================================

log_message "Starting pre-processing for trade date: ${TRADE_DATE}"
log_message "Batch ID: ${BATCH_ID}"

# Create directories if not exist
mkdir -p ${OUTPUT_DIR}
mkdir -p ${ARCHIVE_DIR}
mkdir -p $(dirname ${LOG_FILE})

#===============================================================================
# STEP 1: VALIDATE INPUT FILES
#===============================================================================

TRADE_FILE="${INPUT_DIR}/trades_${TRADE_DATE}.csv"
CONF_FILE="${INPUT_DIR}/confirmations_${TRADE_DATE}.csv"
FEE_FILE="${INPUT_DIR}/fee_schedule_${TRADE_DATE}.csv"

log_message "Validating input files..."

check_file_exists ${TRADE_FILE} || exit 1
check_file_exists ${CONF_FILE} || exit 1
check_file_exists ${FEE_FILE} || exit 1

validate_file_format ${TRADE_FILE} 12 || exit 1
validate_file_format ${CONF_FILE} 8 || exit 1
validate_file_format ${FEE_FILE} 4 || exit 1

log_message "Input files validated successfully"

#===============================================================================
# STEP 2: DATA CLEANSING
#===============================================================================

log_message "Cleansing trade data..."

# Remove header, clean special characters, handle missing values
cat ${TRADE_FILE} | \
    tail -n +2 | \
    sed 's/\r//g' | \
    awk -F',' '{
        # Clean settlement amount: remove commas, handle negative
        gsub(/,/, "", $5)
        # Default empty values
        for(i=1;i<=NF;i++) if($i=="") $i="NULL"
        # Reconstruct line
        for(i=1;i<=NF;i++) printf "%s%s", $i, (i==NF?"\n":",")
    }' > ${OUTPUT_DIR}/trades_clean.tmp

log_message "Trade data cleansed"

# Clean confirmation data
cat ${CONF_FILE} | \
    tail -n +2 | \
    sed 's/\r//g' | \
    awk -F',' '{
        gsub(/,/, "", $3)
        for(i=1;i<=NF;i++) if($i=="") $i="NULL"
        for(i=1;i<=NF;i++) printf "%s%s", $i, (i==NF?"\n":",")
    }' > ${OUTPUT_DIR}/confirmations_clean.tmp

log_message "Confirmation data cleansed"

# Clean fee schedule
cat ${FEE_FILE} | \
    tail -n +2 | \
    sed 's/\r//g' | \
    awk -F',' '{
        for(i=1;i<=NF;i++) if($i=="") $i="NULL"
        for(i=1;i<=NF;i++) printf "%s%s", $i, (i==NF?"\n":",")
    }' > ${OUTPUT_DIR}/fee_schedule_clean.tmp

log_message "Fee schedule cleansed"

#===============================================================================
# STEP 3: DATA VALIDATION
#===============================================================================

log_message "Validating cleansed data..."

# Check for required fields
TRADE_COUNT=$(wc -l < ${OUTPUT_DIR}/trades_clean.tmp)
CONF_COUNT=$(wc -l < ${OUTPUT_DIR}/confirmations_clean.tmp)
FEE_COUNT=$(wc -l < ${OUTPUT_DIR}/fee_schedule_clean.tmp)

log_message "Record counts - Trades: ${TRADE_COUNT}, Confirmations: ${CONF_COUNT}, Fees: ${FEE_COUNT}"

if [[ ${TRADE_COUNT} -eq 0 ]]; then
    log_message "ERROR: No trade records to process"
    exit 1
fi

# Check for duplicate trade IDs
DUP_COUNT=$(cat ${OUTPUT_DIR}/trades_clean.tmp | cut -d',' -f1 | sort | uniq -d | wc -l)
if [[ ${DUP_COUNT} -gt 0 ]]; then
    log_message "WARNING: Found ${DUP_COUNT} duplicate trade IDs"
fi

#===============================================================================
# STEP 4: GENERATE AB INITIO INPUT FILES
#===============================================================================

log_message "Generating Ab Initio input files..."

# Create input file for G_TRADE_CAPTURE
cat ${OUTPUT_DIR}/trades_clean.tmp > ${OUTPUT_DIR}/G_TRADE_CAPTURE_INPUT.dat

# Create input file for G_TRADE_ENRICH
cat ${OUTPUT_DIR}/confirmations_clean.tmp > ${OUTPUT_DIR}/G_TRADE_ENRICH_CONF.dat

# Create fee schedule input for lookup
cat ${OUTPUT_DIR}/fee_schedule_clean.tmp > ${OUTPUT_DIR}/FEE_SCHEDULE_INPUT.dat

log_message "Ab Initio input files generated"

#===============================================================================
# STEP 5: ARCHIVE ORIGINAL FILES
#===============================================================================

log_message "Archiving original files..."

mv ${TRADE_FILE} ${ARCHIVE_DIR}/trades_${TRADE_DATE}_${BATCH_ID}.csv
mv ${CONF_FILE} ${ARCHIVE_DIR}/confirmations_${TRADE_DATE}_${BATCH_ID}.csv
mv ${FEE_FILE} ${ARCHIVE_DIR}/fee_schedule_${TRADE_DATE}_${BATCH_ID}.csv

log_message "Files archived"

#===============================================================================
# STEP 6: TRIGGER AB INITIO GRAPH
#===============================================================================

log_message "Triggering Ab Initio graph G_TRADE_CAPTURE..."

# Trigger Ab Initio graph via air command
air sandbox run G_TRADE_CAPTURE \
    -input_file ${OUTPUT_DIR}/G_TRADE_CAPTURE_INPUT.dat \
    -output_table TRADE_CORE \
    -batch_id ${BATCH_ID} \
    >> ${LOG_FILE} 2>&1

AIR_EXIT_CODE=$?

if [[ ${AIR_EXIT_CODE} -ne 0 ]]; then
    log_message "ERROR: Ab Initio graph G_TRADE_CAPTURE failed with exit code ${AIR_EXIT_CODE}"
    exit 1
fi

log_message "Ab Initio graph G_TRADE_CAPTURE completed successfully"

#===============================================================================
# CLEANUP
#===============================================================================

cleanup_temp_files

log_message "Pre-processing completed successfully for ${TRADE_DATE}"
log_message "Batch ID: ${BATCH_ID}"

exit 0