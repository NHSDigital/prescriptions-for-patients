SHELL=/bin/bash -euo pipefail

guard-%:
	@ if [ "${${*}}" = "" ]; then \
		echo "Environment variable $* not set"; \
		exit 1; \
	fi

#Installs dependencies using poetry.
install-python:
	poetry install

#Installs dependencies using npm.
install-node:
	npm install --legacy-peer-deps

install-hooks: install-python
	poetry run pre-commit install --install-hooks --overwrite

#Condensed Target to run all targets above.
install: install-node install-python install-hooks

#Run the npm linting script (specified in package.json). Used to check the syntax and formatting of files.
lint:
	npm run lint
	find . -name '*.py' -not -path '**/.venv/*' | xargs poetry run flake8
	shellcheck scripts/*.sh

#Removes build/ + dist/ directories
clean:
	rm -rf build
	rm -rf dist
	rm -f test-report.xml
	rm -f smoketest-report.xml

deep-clean: clean
	rm -rf venv
	find . -name 'node_modules' -type d -prune -exec rm -rf '{}' +
	poetry env remove --all

#Creates the fully expanded OAS spec in json
publish: clean
	mkdir -p build
	npm run resolve 2> /dev/null

#Runs build proxy script
build-proxy:
	scripts/build_proxy.sh

#Files to loop over in release
_dist_include="pytest.ini poetry.lock poetry.toml pyproject.toml Makefile build/. tests"

#Create /dist/ sub-directory and copy files into directory
release: clean publish build-proxy
	mkdir -p dist
	for f in $(_dist_include); do cp -r $$f dist; done

#################
# Test commands #
#################

TEST_CMD := @APIGEE_ACCESS_TOKEN=$(APIGEE_ACCESS_TOKEN) \
		poetry run pytest -v \
		--color=yes \
		--api-name=prescriptions-for-patients \
		--proxy-name=$(PROXY_NAME) \
		-s

PROD_TEST_CMD := $(TEST_CMD) \
		--apigee-app-id=$(APIGEE_APP_ID) \
		--apigee-organization=nhsd-prod \
		--status-endpoint-api-key=$(STATUS_ENDPOINT_API_KEY)

#Command to run end-to-end smoketests post-deployment to verify the environment is working
smoketest:
	$(TEST_CMD) \
	--junitxml=smoketest-report.xml \
	-m smoketest

test:
	$(TEST_CMD) \
	--junitxml=test-report.xml \

smoketest-prod:
	$(PROD_TEST_CMD) \
	--junitxml=smoketest-report.xml \
	-m smoketest

test-prod:
	$(PROD_TEST_CMD) \
	--junitxml=test-report.xml \


check-licenses: check-licenses-node check-licenses-python

check-licenses-node:
	npm run check-licenses

check-licenses-python:
	scripts/check_python_licenses.sh

publish-pfp-apigee-release-notes-int:
	dev_tag=$$(curl -s "https://internal-dev.api.service.nhs.uk/prescriptions-for-patients/_ping" | jq --raw-output ".version"); \
	int_tag=$$(curl -s "https://int.api.service.nhs.uk/prescriptions-for-patients/_ping" | jq --raw-output ".version"); \
	echo { \"currentTag\": \"$$int_tag\", \"targetTag\": \"$$dev_tag\", \"repoName\": \"prescriptions-for-patients\", \"targetEnvironment\": \"INT\", \"productName\": \"Prescriptions for Patients Apigee layer\", \"releaseNotesPageId\": \"693750035\", \"releaseNotesPageTitle\": \"Current PfP Apigee layer release notes - INT\" } > /tmp/payload.json
	aws lambda invoke \
		--function-name "release-notes-createReleaseNotes" \
		--cli-binary-format raw-in-base64-out \
		--payload file:///tmp/payload.json /tmp/out.txt
	cat /tmp/out.txt

publish-pfp-apigee-rc-release-notes-int: guard-release_tag guard-current_tag
	echo { \"createReleaseCandidate\": \"true\", \"releasePrefix\": \"PfP-Apigee-\", \"currentTag\": \"$$int_tag\", \"targetTag\": \"$$release_tag\", \"repoName\": \"prescriptions-for-patients\", \"targetEnvironment\": \"INT\", \"productName\": \"Prescriptions for Patients Apigee layer\", \"releaseNotesPageId\": \"710051478\", \"releaseNotesPageTitle\": \"PfP-APigee-$$release_tag - Deployed to [INT] on $$(date +'%d-%m-%y')\" } > /tmp/payload.json
	aws lambda invoke \
		--function-name "release-notes-createReleaseNotes" \
		--cli-binary-format raw-in-base64-out \
		--payload file:///tmp/payload.json /tmp/out.txt
	cat /tmp/out.txt

publish-pfp-apigee-release-notes-prod:
	dev_tag=$$(curl -s "https://internal-dev.api.service.nhs.uk/prescriptions-for-patients/_ping" | jq --raw-output ".version"); \
	prod_tag=$$(curl -s "https://api.service.nhs.uk/prescriptions-for-patients/_ping" | jq --raw-output ".version"); \
	echo { \"currentTag\": \"$$prod_tag\", \"targetTag\": \"$$dev_tag\", \"repoName\": \"prescriptions-for-patients\", \"targetEnvironment\": \"PROD\", \"productName\": \"Prescriptions for Patients Apigee layer\", \"releaseNotesPageId\": \"693750032\", \"releaseNotesPageTitle\": \"Current PfP Apigee layer release notes - PROD\" } > /tmp/payload.json
	aws lambda invoke \
		--function-name "release-notes-createReleaseNotes" \
		--cli-binary-format raw-in-base64-out \
		--payload file:///tmp/payload.json /tmp/out.txt
	cat /tmp/out.txt

mark-jira-released: guard-release_version
	echo { \"releaseVersion\": \"$$release_version\" } > /tmp/payload.json
	aws lambda invoke \
		--function-name "release-notes-markJiraReleased" \
		--cli-binary-format raw-in-base64-out \
		--payload file:///tmp/payload.json /tmp/out.txt
	cat /tmp/out.txt
