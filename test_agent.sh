#!/bin/bash

PIPELINE_PID_FILE="data/logs/pipeline.pid"
WATCHDOG_PID_FILE="data/logs/watchdog.pid"
BACKUP_PID_FILE="data/logs/log_backup.pid"


start_pipeline() {

    # ---------------------------------------------------------
    # Check whether pipeline is already running
    # ---------------------------------------------------------

    if [ -f "$PIPELINE_PID_FILE" ]; then
        PID=$(cat "$PIPELINE_PID_FILE")

        if kill -0 "$PID" 2>/dev/null; then
            echo "Pipeline is already running (PID $PID)."
        else
            rm -f "$PIPELINE_PID_FILE"
        fi
    fi

    if [ ! -f "$PIPELINE_PID_FILE" ]; then

        echo "Starting LFMF monitoring pipeline..."

        PYTHONPATH=src python -m lfmf_monitor.pipeline \
            > /dev/null \
            2>> data/logs/pipeline_errors.log &

        PIPELINE_PID=$!

        echo "$PIPELINE_PID" > "$PIPELINE_PID_FILE"

        disown

        echo "Pipeline started (PID $PIPELINE_PID)."

    fi
}


start_watchdog() {

    # ---------------------------------------------------------
    # Check whether watchdog is already running
    # ---------------------------------------------------------

    if [ -f "$WATCHDOG_PID_FILE" ]; then
        WATCHDOG_PID=$(cat "$WATCHDOG_PID_FILE")

        if kill -0 "$WATCHDOG_PID" 2>/dev/null; then
            echo "Watchdog is already running (PID $WATCHDOG_PID)."
            return
        fi

        rm -f "$WATCHDOG_PID_FILE"
    fi

    echo "Starting LFMF watchdog..."

    PYTHONPATH=src python -m lfmf_monitor.watchdog \
        > /dev/null \
        2>> data/logs/errors.log &

    WATCHDOG_PID=$!

    echo "$WATCHDOG_PID" > "$WATCHDOG_PID_FILE"

    disown

    echo "Watchdog started (PID $WATCHDOG_PID)."
}


start_backup() {

    # ---------------------------------------------------------
    # Check whether backup process is already running
    # ---------------------------------------------------------

    if [ -f "$BACKUP_PID_FILE" ]; then
        BACKUP_PID=$(cat "$BACKUP_PID_FILE")

        if kill -0 "$BACKUP_PID" 2>/dev/null; then
            echo "Log backup is already running (PID $BACKUP_PID)."
            return
        fi

        rm -f "$BACKUP_PID_FILE"
    fi

    echo "Starting LFMF log backup..."

    PYTHONPATH=src python -m lfmf_monitor.backup \
        > /dev/null \
        2>> data/logs/errors.log &

    BACKUP_PID=$!

    echo "$BACKUP_PID" > "$BACKUP_PID_FILE"

    disown

    echo "Log backup started (PID $BACKUP_PID)."
}


start_all() {

    # ---------------------------------------------------------
    # Make sure log directory exists
    # ---------------------------------------------------------

    mkdir -p data/logs

    # ---------------------------------------------------------
    # Start all three independent processes
    # ---------------------------------------------------------

    start_pipeline
    start_watchdog
    start_backup

    echo
    echo "LFMF monitoring system started."
}


stop_pipeline() {

    # ---------------------------------------------------------
    # Stop pipeline
    # ---------------------------------------------------------

    if [ ! -f "$PIPELINE_PID_FILE" ]; then
        echo "Pipeline is not running."
    else
        PID=$(cat "$PIPELINE_PID_FILE")

        if kill -0 "$PID" 2>/dev/null; then
            echo "Stopping LFMF pipeline (PID $PID)..."

            kill "$PID"

            sleep 1

            if kill -0 "$PID" 2>/dev/null; then
                echo "Pipeline did not stop. Force stopping..."
                kill -9 "$PID"
            fi

            echo "Pipeline stopped."
        else
            echo "Pipeline process is no longer running."
        fi

        rm -f "$PIPELINE_PID_FILE"
    fi


    # ---------------------------------------------------------
    # Stop watchdog
    #
    # The watchdog is stopped only when the user explicitly
    # runs ./lfmf.sh stop.
    #
    # If the pipeline crashes by itself, this section is never
    # executed, so the watchdog remains running.
    # ---------------------------------------------------------

    if [ -f "$WATCHDOG_PID_FILE" ]; then
        WATCHDOG_PID=$(cat "$WATCHDOG_PID_FILE")

        if kill -0 "$WATCHDOG_PID" 2>/dev/null; then
            echo "Stopping LFMF watchdog (PID $WATCHDOG_PID)..."

            kill "$WATCHDOG_PID"

            sleep 1

            if kill -0 "$WATCHDOG_PID" 2>/dev/null; then
                echo "Watchdog did not stop. Force stopping..."
                kill -9 "$WATCHDOG_PID"
            fi

            echo "Watchdog stopped."
        else
            echo "Watchdog process is no longer running."
        fi

        rm -f "$WATCHDOG_PID_FILE"
    fi


    # ---------------------------------------------------------
    # Stop independent backup process
    # ---------------------------------------------------------

    if [ -f "$BACKUP_PID_FILE" ]; then
        BACKUP_PID=$(cat "$BACKUP_PID_FILE")

        if kill -0 "$BACKUP_PID" 2>/dev/null; then
            echo "Stopping LFMF log backup (PID $BACKUP_PID)..."

            kill "$BACKUP_PID"

            sleep 1

            if kill -0 "$BACKUP_PID" 2>/dev/null; then
                echo "Log backup did not stop. Force stopping..."
                kill -9 "$BACKUP_PID"
            fi

            echo "Log backup stopped."
        else
            echo "Log backup process is no longer running."
        fi

        rm -f "$BACKUP_PID_FILE"
    fi
}


status_pipeline() {

    echo "----------------------------------------"
    echo "LFMF Monitoring Status"
    echo "----------------------------------------"


    # ---------------------------------------------------------
    # Pipeline status
    # ---------------------------------------------------------

    if [ -f "$PIPELINE_PID_FILE" ]; then
        PID=$(cat "$PIPELINE_PID_FILE")

        if kill -0 "$PID" 2>/dev/null; then
            echo "Pipeline : RUNNING (PID $PID)."
        else
            echo "Pipeline : NOT RUNNING."
        fi
    else
        echo "Pipeline : NOT RUNNING."
    fi


    # ---------------------------------------------------------
    # Watchdog status
    # ---------------------------------------------------------

    if [ -f "$WATCHDOG_PID_FILE" ]; then
        WATCHDOG_PID=$(cat "$WATCHDOG_PID_FILE")

        if kill -0 "$WATCHDOG_PID" 2>/dev/null; then
            echo "Watchdog : RUNNING (PID $WATCHDOG_PID)."
        else
            echo "Watchdog : NOT RUNNING."
        fi
    else
        echo "Watchdog : NOT RUNNING."
    fi


    # ---------------------------------------------------------
    # Backup status
    # ---------------------------------------------------------

    if [ -f "$BACKUP_PID_FILE" ]; then
        BACKUP_PID=$(cat "$BACKUP_PID_FILE")

        if kill -0 "$BACKUP_PID" 2>/dev/null; then
            echo "Log backup : RUNNING (PID $BACKUP_PID)."
        else
            echo "Log backup : NOT RUNNING."
        fi
    else
        echo "Log backup : NOT RUNNING."
    fi


    echo "----------------------------------------"
}


case "$1" in

    start)
        start_all
        ;;

    stop)
        stop_pipeline
        ;;

    restart)
        stop_pipeline
        start_all
        ;;

    status)
        status_pipeline
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;

esac