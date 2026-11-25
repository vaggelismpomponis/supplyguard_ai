uv python install 3.12
uv python pin 3.12
uv sync --reinstall

uv python list

chainlit run src/ui/app.py