SHELL := /bin/bash

BACKEND_DIR   := ML/files
FRONTEND_DIR  := frontend
VENV_ACTIVATE := backend/.venv/Scripts/activate

.PHONY: dev backend frontend install install-backend install-frontend help

help:
	@echo ""
	@echo "FairLens — available targets"
	@echo "  make dev               start backend + frontend together"
	@echo "  make backend           start FastAPI backend only  (port 8000)"
	@echo "  make frontend          start Next.js frontend only (port 3000)"
	@echo "  make install           install all dependencies"
	@echo "  make install-backend   pip install into venv"
	@echo "  make install-frontend  npm install"
	@echo ""

## Start both services concurrently.
## Ctrl-C kills both.
dev:
	@echo ">> Starting backend (port 8000) and frontend (port 3000) ..."
	@trap 'kill 0' INT; \
	 { source $(VENV_ACTIVATE) && cd "$(BACKEND_DIR)" && uvicorn main:app --reload --port 8000; } & \
	 { cd $(FRONTEND_DIR) && npm run dev; } & \
	 wait

## FastAPI backend only
backend:
	source $(VENV_ACTIVATE) && cd "$(BACKEND_DIR)" && uvicorn main:app --reload --port 8000

## Next.js frontend only
frontend:
	cd $(FRONTEND_DIR) && npm run dev

## Install everything
install: install-backend install-frontend

install-backend:
	source $(VENV_ACTIVATE) && pip install -r "$(BACKEND_DIR)/requirements.txt"

install-frontend:
	cd $(FRONTEND_DIR) && npm install
