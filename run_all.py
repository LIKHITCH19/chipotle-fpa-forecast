"""Rebuild everything from the raw data.

    python run_all.py                 # assumes data/raw is already downloaded
    python run_all.py --download      # download first (needs SEC_USER_AGENT in .env)
"""
import subprocess
import sys

steps = ["src/extract_cmg.py", "src/extract_peers.py", "src/check_data.py", "src/run_model.py",
         "src/baseline_forecast.py", "src/score_forecast.py", "src/make_charts.py", "src/make_tableau_data.py"]
if "--download" in sys.argv:
    steps.insert(0, "src/fetch_data.py")

for step in steps:
    print(f"\n== {step}")
    subprocess.run([sys.executable, step], check=True)
