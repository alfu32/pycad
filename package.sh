if [[ -d .venv ]]; then
  echo 'venv does exist'
  else
  echo 'venv does not exist'
  python -m venv .venv
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  python -m pip install PyInstaller
fi

source ./.venv/Scripts/activate  # On Windows, use `venv\Scripts\activate`
python -m PyInstaller --onefile pycad/main.py




