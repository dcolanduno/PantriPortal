"""Open the private one-time setup link without printing its token."""
from pathlib import Path
import webbrowser,os
root=Path(__file__).resolve().parents[1]
data=Path(os.environ.get('PANTRY_DATA',str(root/'work/runtime')))
token=data/'admin-setup-token'
if not token.is_file():
 raise SystemExit('Administrator setup has already been used, or the local server has not started yet.')
webbrowser.open('http://127.0.0.1:8767/#admin-setup='+token.read_text().strip())
