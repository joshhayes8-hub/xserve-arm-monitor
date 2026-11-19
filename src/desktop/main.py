#!/usr/bin/env python3
"""Xserve ARM Monitor - native KDE desktop client."""
import json
import sys
import os
from urllib.request import urlopen

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QFrame, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QSizePolicy
)

API = os.environ.get("XARMC_API", "http://127.0.0.1:5000")


def get_json(path):
    with urlopen(API + path, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


class Panel(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setObjectName("panel")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 18, 20, 18)
        self.layout.setSpacing(10)
        heading = QLabel(title)
        heading.setObjectName("panelTitle")
        self.layout.addWidget(heading)


class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Xserve ARM Monitor")
        self.resize(1280, 900)
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(26, 22, 26, 22)
        root_layout.setSpacing(18)
        root.setMinimumHeight(1320)

        header = QHBoxLayout()
        brand = QVBoxLayout()
        title = QLabel("Xserve ARM Monitor")
        title.setObjectName("mainTitle")
        subtitle = QLabel("Automatic Ripping Machine · Server dashboard")
        subtitle.setObjectName("muted")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch()
        self.connection = QLabel("● Backend connected")
        self.connection.setObjectName("green")
        header.addWidget(self.connection)
        root_layout.addLayout(header)

        cards = QGridLayout()
        cards.setSpacing(16)
        self.service_value = self.metric_card(cards, 0, "ARM Service", "Checking...", "ARM web interface")
        self.activity_value = self.metric_card(cards, 1, "Ripping Activity", "Checking...", "Latest job status")
        self.latest_value = self.metric_card(cards, 2, "Recent Job", "—", "Most recently recorded disc")
        root_layout.addLayout(cards)

        activity = Panel("Current Activity")
        activity.setMinimumHeight(245)
        self.activity_status = QLabel("Loading...")
        self.activity_status.setObjectName("activityStatus")
        self.activity_status.setMinimumHeight(42)
        self.activity_status.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        activity.layout.addWidget(self.activity_status)
        self.stage = QLabel("Checking ARM activity")
        self.stage.setObjectName("muted")
        activity.layout.addWidget(self.stage)
        self.filename = QLabel("")
        self.filename.setObjectName("fileName")
        activity.layout.addWidget(self.filename)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(12)
        activity.layout.addWidget(self.progress)
        self.progress_text = QLabel("No progress data")
        self.progress_text.setObjectName("muted")
        activity.layout.addWidget(self.progress_text)
        self.details = QLabel("")
        self.details.setObjectName("muted")
        activity.layout.addWidget(self.details)
        root_layout.addWidget(activity)

        cpu = Panel("CPU Monitoring")
        cpu.setMinimumHeight(540)
        self.overall_label = QLabel("Overall Server CPU Usage     --%")
        cpu.layout.addWidget(self.overall_label)
        self.overall_bar = QProgressBar()
        self.overall_bar.setFixedHeight(12)
        self.overall_bar.setTextVisible(False)
        cpu.layout.addWidget(self.overall_bar)
        packages = QHBoxLayout()
        self.core_labels = []
        self.package_labels = []
        for package in range(2):
            box = Panel(f"Xeon {package + 1}")
            box.setMinimumHeight(340)
            heading = box.layout.itemAt(0).widget()
            box.layout.removeWidget(heading)
            heading.setStyleSheet("font-size: 18px;")
            header_row = QHBoxLayout()
            header_row.addWidget(heading)
            header_row.addStretch()
            temp = QLabel("<b>--°C</b><br><span style='color:#93a1b2'>Average temperature</span>")
            temp.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            header_row.addWidget(temp)
            box.layout.insertLayout(0, header_row)
            usage_heading = QLabel("PROCESSOR USAGE")
            usage_heading.setObjectName("muted")
            box.layout.addWidget(usage_heading)
            usage_bar = QProgressBar()
            usage_bar.setRange(0, 100)
            usage_bar.setTextVisible(False)
            usage_bar.setFixedHeight(12)
            box.layout.addWidget(usage_bar)
            usage_value = QLabel("--%")
            usage_value.setAlignment(Qt.AlignRight)
            box.layout.addWidget(usage_value)
            cores_row = QHBoxLayout()
            cores_row.setSpacing(8)
            for core in range(4):
                meter_widget = QWidget()
                meter = QVBoxLayout(meter_widget)
                meter.setContentsMargins(4, 0, 4, 0)
                meter.setSpacing(0)
                value = QLabel("--%")
                value.setAlignment(Qt.AlignCenter)
                value.setFixedHeight(24)
                bar = QProgressBar()
                bar.setOrientation(Qt.Vertical)
                bar.setRange(0, 100)
                bar.setTextVisible(False)
                bar.setFixedSize(88, 86)
                meter.addWidget(value)
                meter.addWidget(bar, alignment=Qt.AlignHCenter)
                meter.addSpacing(16)
                name = QLabel(f"Core {core}")
                name.setObjectName("muted")
                name.setAlignment(Qt.AlignCenter)
                name.setFixedHeight(24)
                meter.addWidget(name)
                cores_row.addWidget(meter_widget, 1)
                self.core_labels.append((value, bar))
            box.layout.addLayout(cores_row)
            self.package_labels.append((temp, usage_bar, usage_value))
            packages.addWidget(box)
        cpu.layout.addLayout(packages)
        root_layout.addWidget(cpu)

        jobs = Panel("Recent Jobs")
        jobs.setMinimumHeight(190)
        self.jobs = QTableWidget(0, 6)
        self.jobs.setHorizontalHeaderLabels(["Job", "Title", "Status", "Started", "Finished", "Errors"])
        self.jobs.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.jobs.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.jobs.verticalHeader().hide()
        self.jobs.setEditTriggers(QTableWidget.NoEditTriggers)
        self.jobs.setSelectionBehavior(QTableWidget.SelectRows)
        jobs.layout.addWidget(self.jobs)
        root_layout.addWidget(jobs)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)
        self.setStyleSheet("""
            QMainWindow { background: #10151d; color: #edf2f7; }
            QWidget { color: #edf2f7; font-family: 'Noto Sans'; font-size: 13px; }
            QLabel { background: transparent; border: none; }
            QFrame#panel { background: #1a222e; border: 1px solid #2b3746; border-radius: 12px; }
            QLabel#mainTitle { font-size: 22px; font-weight: 700; }
            QLabel#panelTitle { font-size: 15px; font-weight: 600; }
            QLabel#muted { color: #93a1b2; }
            QLabel#green { color: #42c987; font-weight: 600; }
            QLabel#fileName { font-size: 15px; font-weight: 600; }
            QLabel#activityStatus { background: transparent; border: none; font-size: 26px; font-weight: 700; padding-top: 2px; padding-bottom: 4px; }
            QProgressBar { background: #303c4c; border: none; border-radius: 5px; }
            QProgressBar::chunk { background: #42c987; border-radius: 5px; }
            QTableWidget { background: #151c26; alternate-background-color: #1a222e; gridline-color: #2b3746; border: 1px solid #2b3746; }
            QHeaderView::section { background: #202a37; color: #93a1b2; padding: 9px; border: none; }
        """)

        self.refresh_all()
        self.dashboard_timer = QTimer(self)
        self.dashboard_timer.timeout.connect(self.refresh_all)
        self.dashboard_timer.start(5000)
        self.cpu_timer = QTimer(self)
        self.cpu_timer.timeout.connect(self.refresh_cpu)
        self.cpu_timer.start(3000)

    def metric_card(self, grid, column, heading, value, note):
        card = Panel(heading)
        label = QLabel(value)
        label.setObjectName("metric")
        label.setStyleSheet("font-size: 25px; font-weight: 650;")
        desc = QLabel(note)
        desc.setObjectName("muted")
        card.layout.addWidget(label)
        card.layout.addWidget(desc)
        grid.addWidget(card, 0, column)
        return label

    def refresh_all(self):
        try:
            jobs = get_json("/api/jobs")
            service = get_json("/api/service")
            activity = get_json("/api/activity")
            self.connection.setText("● Backend connected")
            self.service_value.setText("Active" if service.get("status") == "active" else "Inactive")
            self.activity_value.setText(activity.get("activity", "Unknown"))
            self.latest_value.setText(jobs[0].get("title") or "Unknown" if jobs else "No jobs")
            activity_name = activity.get("activity", "Idle")
            self.activity_status.setText(activity_name)
            if activity_name == "Failed":
                activity_colour = "#ff6262"
            elif activity_name in ("Completed", "Ripping", "Scanning disc"):
                activity_colour = "#42c98b"
            elif activity_name == "Transcoding":
                activity_colour = "#60a5fa"
            elif "Waiting" in activity_name:
                activity_colour = "#f5b942"
            else:
                activity_colour = "#e8eef7"
            self.activity_status.setStyleSheet(f"color: {activity_colour};")
            self.stage.setText(
                f"File {activity['current_file_number']} of {activity['total_files']}"
                if activity.get("current_file_number") and activity.get("total_files")
                else activity.get("stage") or "No processing stage available"
            )
            self.filename.setText("Current file: " + activity["current_file"] if activity.get("current_file") else "")
            progress = activity.get("progress")
            self.progress.setValue(int(progress or 0) if activity.get("active") else 0)
            self.progress_text.setText(f"{progress}% current operation progress" if progress is not None and activity.get("active") else "No live progress — job is not running")
            details = []
            if activity.get("fps") is not None:
                details.append(f"{activity['fps']} FPS")
            if activity.get("eta"):
                details.append("ETA: " + activity["eta"])
            if activity.get("job_id") is not None:
                details.append(f"Job #{activity['job_id']}")
            self.details.setText("  ·  ".join(details))
            self.jobs.setRowCount(len(jobs))
            for row, job in enumerate(jobs):
                values = [job.get("job_id"), job.get("title"), job.get("status"), job.get("start_time"), job.get("stop_time"), job.get("errors")]
                for col, value in enumerate(values):
                    self.jobs.setItem(row, col, QTableWidgetItem(str(value or "—")))
        except Exception as exc:
            self.connection.setText("● Backend unavailable")
            self.connection.setStyleSheet("color: #ff6565;")
            self.details.setText(str(exc))

    def refresh_cpu(self):
        try:
            data = get_json("/api/cpu")
            overall = data.get("overall")
            self.overall_label.setText(f"Overall Server CPU Usage     {overall if overall is not None else '--'}%")
            self.overall_bar.setValue(int(overall or 0))
            mappings = [[0, 1, 4, 2], [5, 7, 3, 6]]
            for package, mapping in enumerate(mappings):
                values = [data.get("cores", {}).get(f"cpu{cpu}") for cpu in mapping]
                valid = [v for v in values if v is not None]
                average = sum(valid) / len(valid) if valid else None
                temp = data.get("temperatures", {}).get(str(package), data.get("temperatures", {}).get(package))
                self.package_labels[package][0].setText(f"<b>{temp:.1f}°C</b><br><span style='color:#93a1b2'>Average temperature</span>" if temp is not None else "<b>--°C</b><br><span style='color:#93a1b2'>Average temperature</span>")
                usage_bar = self.package_labels[package][1]
                usage_value = self.package_labels[package][2]
                usage_bar.setValue(int(average or 0))
                usage_value.setText(f"{average:.1f}%" if average is not None else "--%")
                for slot, cpu in enumerate(mapping):
                    value, bar = self.core_labels[package * 4 + slot]
                    usage = data.get("cores", {}).get(f"cpu{cpu}")
                    value.setText(f"{usage:.1f}%" if usage is not None else "--%")
                    bar.setValue(int(usage or 0))
        except Exception:
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec())