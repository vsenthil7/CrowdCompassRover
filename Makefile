# CrowdCompass Rover — developer & supply-chain tasks.
.PHONY: test test-frontend e2e sbom pip-audit docker-build docker-up

# Backend test suite with the 100% coverage gate.
test:
	cd backend && pytest

# Frontend tests with coverage.
test-frontend:
	cd frontend && npx vitest run --coverage

# Playwright end-to-end journeys.
e2e:
	cd e2e && npm test

# Supply-chain: CycloneDX SBOM of the installed backend environment.
sbom:
	cd backend && cyclonedx-py environment --output-format JSON -o sbom.cdx.json
	@echo "SBOM written to backend/sbom.cdx.json"

# Supply-chain: dependency CVE audit.
pip-audit:
	cd backend && pip-audit --output json -o audit-report.json || true
	@echo "Audit written to backend/audit-report.json"

# Build the container images (mock-mode by default).
docker-build:
	docker build -t crowdcompass-rover-backend:dev backend/
	docker build -t crowdcompass-rover-frontend:dev frontend/

# Bring up the local stack (backend mock + frontend).
docker-up:
	docker compose up --build
