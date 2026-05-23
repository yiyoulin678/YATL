.PHONY: lint
lint:
	poetry run ruff check .

.PHONY: format
format:
	poetry run ruff check --select I --fix .
	poetry run ruff format .

typing:
	poetry run mypy .

.PHONY: integration_tests
integration_tests:
	poetry run yatl ./integration_tests

.PHONY: unit_tests
unit_tests:
	poetry run pytest

clear_env:
	poetry env remove --all 