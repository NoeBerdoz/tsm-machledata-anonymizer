"""Start the local user interface: uv run python -m pii_anonymizer"""

import sys
from pathlib import Path

from streamlit.web import cli

# By default Streamlit listens on the whole network, sends usage statistics, blocks the first
# start to ask for an e-mail address, and shows a button to deploy the app to its cloud.
sys.argv = [
    "streamlit",
    "run",
    str(Path(__file__).with_name("app.py")),
    "--server.address=127.0.0.1",
    "--browser.gatherUsageStats=false",
    "--server.showEmailPrompt=false",
    "--client.toolbarMode=minimal",
]
cli.main()
