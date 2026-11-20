
from flask import Flask, jsonify, render_template
import sqlite3
import subprocess
import os
import re
from pathlib import Path

app = Flask(__name__)

DB_PATH = os.environ.get("ARM_DB_PATH", "/home/arm/db/arm.db")
ARM_LOG_DIR = Path(os.environ.get("ARM_LOG_DIR", "/home/arm/logs"))
ARM_SERVICE_NAME = os.environ.get("ARM_SERVICE_NAME", "armui")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/service")
def service():
    result = subprocess.run(
        ["systemctl", "is-active", ARM_SERVICE_NAME],
        capture_output=True,
        text=True
    )

    return jsonify({
        "service": ARM_SERVICE_NAME,
        "status": result.stdout.strip()
    })


@app.route("/api/jobs")
def jobs():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    rows = connection.execute("""
        SELECT job_id, title, status, start_time,
       stop_time, no_of_titles, errors, logfile, path
        FROM job
        ORDER BY job_id DESC
        LIMIT 10
    """).fetchall()

    connection.close()

    return jsonify([dict(row) for row in rows])


@app.route("/api/activity")
def activity():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    job = connection.execute("""
        SELECT job_id, title, status, start_time, stop_time,
               no_of_titles, logfile, path, errors
        FROM job
        ORDER BY job_id DESC
        LIMIT 1
    """).fetchone()

    connection.close()

    if job is None:
        return jsonify({"activity": "Idle", "message": "No jobs recorded"})

    data = dict(job)
    status = data["status"]
    active = data["stop_time"] is None and status not in ("success", "fail")

    if status == "fail":
        activity_status = "Failed"
    elif status == "success":
        activity_status = "Completed"
    elif status == "transcoding":
        activity_status = "Transcoding"
    elif status == "ripping":
        activity_status = "Ripping"
    elif status == "info":
        activity_status = "Scanning disc"
    elif status == "waiting_transcode":
        activity_status = "Waiting for transcoding"
    elif status == "waiting":
        activity_status = "Waiting"
    elif active:
        activity_status = "Processing"
    else:
        activity_status = "Idle"

    result = {
        "job_id": data["job_id"],
        "title": data["title"],
        "activity": activity_status,
        "active": active,
        "status": status,
        "stage": None,
	"current_file": None,
        "current_file_number": None,
        "total_files": None,
        "progress": None,
        "fps": None,
        "eta": None,
        "current_title": None,
        "total_titles": data["no_of_titles"],
        "errors": data["errors"],
        "latest_log": None
    }

    # Read the MakeMKV progress file
    progress_file = ARM_LOG_DIR / "progress" / f"{data['job_id']}.log"

    if progress_file.is_file():
        lines = progress_file.read_text(errors="replace").splitlines()

        for line in reversed(lines):
            if line.startswith("PRGV:") and result["progress"] is None:
                match = re.search(r"PRGV:(\d+),(\d+),(\d+)", line)
                if match:
                    current, _, maximum = map(int, match.groups())
                    if maximum:
                        result["progress"] = round(current / maximum * 100, 1)

            elif line.startswith("PRGC:") and result["stage"] is None:
                match = re.search(r'PRGC:\d+,\d+,"([^"]+)"', line)
                if match:
                    result["stage"] = match.group(1)

            elif result["progress"] is not None and result["stage"] is not None:
                break

    # Read the job log, including HandBrake progress
    logfile = data.get("logfile")

    if logfile and Path(logfile).name == logfile:
        log_path = ARM_LOG_DIR / logfile

        if log_path.is_file():
            lines = log_path.read_text(errors="replace").splitlines()

            if lines:
                result["latest_log"] = lines[-1][-500:]
            # ARM logs each source file as it enters the transcode queue.
            # HandBrake's own "task 1 of 1" is per-file progress, not the
            # position within the disc's full set of episodes.
            transcode_files = []
            for line in lines:
                match = re.search(
                    r"""Transcoding file (.+?) to (.+?)\s*$""",
                    line
                )
                if match:
                    source = match.group(1).strip().strip("'").strip('"')
                    destination = match.group(2).strip().strip("'").strip('"')
                    transcode_files.append((Path(source).name, Path(destination).name))

                match = re.search(
                    r"Processing track #(\d+) of (\d+)",
                    line
                )
                if match:
                    result["total_files"] = int(match.group(2))

            if transcode_files:
                result["current_file_number"] = len(transcode_files)
                result["current_file"] = transcode_files[-1][0]
            for line in reversed(lines):
                match = re.search(
                    r"Encoding: task (\d of \d), (\d{1,3}\.\d{2}) %.*?"
                    r"\((\d+\.\d+) fps, avg (\d+\.\d+) fps, ETA ([\dhms]*?)\)",
                    line
                )
                if match:
                    result["stage"] = f"HandBrake task {match.group(1)}"
                    result["progress"] = float(match.group(2))
                    result["fps"] = float(match.group(3))
                    result["eta"] = match.group(5)
                    break

                match = re.search(r"Processing track #(\d{1,2}) of (\d{1,2})", line)
                if match and result["current_title"] is None:
                    result["current_title"] = int(match.group(1))
                    result["total_titles"] = int(match.group(2))

    return jsonify(result)

# CPU monitoring
import threading

cpu_lock = threading.Lock()
previous_cpu_stats = {}


def read_cpu_stats():
    stats = {}

    with open("/proc/stat") as f:
        for line in f:
            parts = line.split()

            if not parts or not (
                parts[0] == "cpu" or parts[0].startswith("cpu")
                and parts[0][3:].isdigit()
            ):
                continue

            stats[parts[0]] = [int(value) for value in parts[1:]]

    return stats


def calculate_cpu_usage(current, previous):
    if previous is None:
        return None

    total_current = sum(current)
    total_previous = sum(previous)

    idle_current = current[3] + (current[4] if len(current) > 4 else 0)
    idle_previous = previous[3] + (previous[4] if len(previous) > 4 else 0)

    total_delta = total_current - total_previous
    idle_delta = idle_current - idle_previous

    if total_delta <= 0:
        return 0.0

    return round((total_delta - idle_delta) / total_delta * 100, 1)


@app.route("/api/cpu")
def cpu_monitor():
    global previous_cpu_stats

    current_stats = read_cpu_stats()

    with cpu_lock:
        overall = calculate_cpu_usage(
            current_stats.get("cpu"),
            previous_cpu_stats.get("cpu")
        )

        cores = {}

        for cpu in range(8):
            key = f"cpu{cpu}"
            cores[key] = calculate_cpu_usage(
                current_stats.get(key),
                previous_cpu_stats.get(key)
            )

        previous_cpu_stats = current_stats

    temperatures = {}

    for hwmon in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            if (hwmon / "name").read_text().strip() != "coretemp":
                continue

            device_name = (hwmon / "device").resolve().name
            package = int(device_name.split(".")[-1])

            readings = []

            for sensor in hwmon.glob("temp*_input"):
                readings.append(int(sensor.read_text().strip()) / 1000)

            if readings:
                temperatures[package] = round(
                    sum(readings) / len(readings), 1
                )

        except (OSError, ValueError, IndexError):
            continue

    return jsonify({
        "overall": overall,
        "cores": cores,
        "temperatures": temperatures
    })

if __name__ == "__main__":
    app.run(host=os.environ.get("ARM_CONTROL_HOST", "0.0.0.0"), port=int(os.environ.get("ARM_CONTROL_PORT", "5000")))
