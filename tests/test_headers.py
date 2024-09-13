"""
See
https://github.com/NHSDigital/pytest-nhsd-apim/blob/main/tests/test_examples.py
for more ideas on how to test the authorization of your API.
"""

import pytest
import requests
import uuid


@pytest.mark.nhsd_apim_authorization(
    {
        "access": "patient",
        "level": "P9",
        "login_form": {"username": "9912003071"},
        "authentication": "separate",
    }
)
@pytest.mark.parametrize("x_request_id", [pytest.param("invalid"), pytest.param("")])
def test_expected_content_type_headers_when_x_request_id_invalid(
    x_request_id, nhsd_apim_proxy_url, nhsd_apim_auth_headers
):
    request_headers = nhsd_apim_auth_headers
    request_headers["X-Request-Id"] = x_request_id
    request_headers["X-Correlation-ID"] = str(uuid.uuid4())
    resp = requests.get(f"{nhsd_apim_proxy_url}/Bundle", headers=request_headers)

    assert resp.status_code == 400
    assert resp.headers["Content-Type"] == "application/fhir+json"
