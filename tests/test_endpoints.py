"""
See
https://github.com/NHSDigital/pytest-nhsd-apim/blob/main/tests/test_examples.py
for more ideas on how to test the authorization of your API.
"""

from os import getenv
import pytest
import requests
import uuid


@pytest.mark.smoketest
def test_ping(nhsd_apim_proxy_url):
    resp = requests.get(f"{nhsd_apim_proxy_url}/_ping")
    assert resp.status_code == 200


@pytest.mark.smoketest
def test_wait_for_ping(nhsd_apim_proxy_url):
    retries = 0
    resp = requests.get(f"{nhsd_apim_proxy_url}/_ping")
    deployed_commitId = resp.json().get("commitId")

    while (
        deployed_commitId != getenv("SOURCE_COMMIT_ID")
        and retries <= 30
        and resp.status_code == 200
    ):
        resp = requests.get(f"{nhsd_apim_proxy_url}/_ping")
        deployed_commitId = resp.json().get("commitId")
        retries += 1

    if resp.status_code != 200:
        pytest.fail(f"Status code {resp.status_code}, expecting 200")
    elif retries >= 30:
        pytest.fail("Timeout Error - max retries")

    assert deployed_commitId == getenv("SOURCE_COMMIT_ID")


@pytest.mark.smoketest
def test_status(nhsd_apim_proxy_url, status_endpoint_auth_headers):
    resp = requests.get(
        f"{nhsd_apim_proxy_url}/_status", headers=status_endpoint_auth_headers
    )
    assert resp.status_code == 200
    # Make some additional assertions about your status response here!


@pytest.mark.smoketest
def test_wait_for_status(nhsd_apim_proxy_url, status_endpoint_auth_headers):
    retries = 0
    resp = requests.get(
        f"{nhsd_apim_proxy_url}/_status", headers=status_endpoint_auth_headers
    )
    deployed_commitId = resp.json().get("commitId")
    deployment_status = resp.json().get("status")

    while (
        deployed_commitId != getenv("SOURCE_COMMIT_ID")
        and retries <= 30
        and resp.status_code == 200
        and resp.json().get("version")
    ):
        resp = requests.get(
            f"{nhsd_apim_proxy_url}/_status", headers=status_endpoint_auth_headers
        )
        deployed_commitId = resp.json().get("commitId")
        retries += 1

    if resp.status_code != 200:
        pytest.fail(f"Status code {resp.status_code}, expecting 200")
    elif retries >= 30:
        pytest.fail("Timeout Error - max retries")
    elif not resp.json().get("version"):
        pytest.fail("version not found")

    assert deployed_commitId == getenv("SOURCE_COMMIT_ID")
    assert deployment_status == "pass"


@pytest.mark.nhsd_apim_authorization(
    {
        "access": "patient",
        "level": "P9",
        "login_form": {"username": "9912003071"},
        "authentication": "separate",
    }
)
def test_authed_patient_can_access_bundle_endpoint(
    nhsd_apim_proxy_url, nhsd_apim_auth_headers
):
    request_headers = nhsd_apim_auth_headers
    request_headers["X-Request-Id"] = str(uuid.uuid4())
    request_headers["X-Correlation-ID"] = str(uuid.uuid4())
    resp = requests.get(f"{nhsd_apim_proxy_url}/Bundle", headers=request_headers)
    assert resp.status_code == 200


@pytest.mark.smoketest
def test_un_authed_request_can_access_metadata_endpoint(nhsd_apim_proxy_url):
    resp = requests.get(f"{nhsd_apim_proxy_url}/metadata", headers=None)
    assert resp.status_code == 200
