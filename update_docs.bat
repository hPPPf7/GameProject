@echo off
call myenv\Scripts\activate
python scripts\generate_docs.py
mkdocs serve
