
.PHONY: install
install:
	pip install -r requirements.txt --use-mirrors

.PHONY: pep8
pep8:
	@flake8 . --ignore=E501,F403,E126,E127,E128,E303
