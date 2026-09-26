#!/bin/bash

PID_FILE="data/pipeline.pid"

start_pipeline() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")

        if kill -0 "$PID" 2>/dev/null; then
            echo "Pipeline is already running (PID $PID)."
            return
        fi

        rm -f "$PID_FILE"
    fi

    echo "Starting LFMF monitoring pipeline..."

    PYTHONPATH=src python -m lfmf_monitor.pipeline > /dev/null 2>&1 &

    PID=$!
    echo "$PID" > "$PID_FILE"

    disown

    echo "Pipeline started (PID $PID)."
}

stop_pipeline() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Pipeline is not running."
        return
    fi

    PID=$(cat "$PID_FILE")

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

    rm -f "$PID_FILE"
}

status_pipeline() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")

        if kill -0 "$PID" 2>/dev/null; then
            echo "Pipeline is running (PID $PID)."
            return
        fi
    fi

    echo "Pipeline is not running."
}

case "$1" in
    start)
        start_pipeline
        ;;
    stop)
        stop_pipeline
        ;;
    restart)
        stop_pipeline
        start_pipeline
        ;;
    status)
        status_pipeline
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac