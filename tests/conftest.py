import pytest


@pytest.fixture()
def nhsd_apim_proxy_url():
    return "https://internal-dev.api.service.nhs.uk/prescriptions-for-patients"