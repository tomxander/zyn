# Opens the OLD Streamlit review screen. The current screen is review.ps1.
Set-Location $PSScriptRoot
.\.venv\Scripts\python.exe -m streamlit run harness\review\app.py --server.headless false --browser.gatherUsageStats false
