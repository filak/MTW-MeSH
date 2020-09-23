@echo off
sqlite3 mtw.db ".backup mtw_db.bak"
sqlite3 mtw.db vacuum