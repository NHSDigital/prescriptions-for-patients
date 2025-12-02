#
# Script to test delegated access flow
# Reference: https://nhsd-confluence.digital.nhs.uk/spaces/APM/pages/1171199043/
#            KOP-108+Using+Keycloak+to+generate+composite+id+tokens+for+testing+delegation
#
import time
import uuid

import jwt
import os
import requests
from dataclasses import dataclass
import logging
from dotenv import load_dotenv

load_dotenv()
APIM_ENV = os.getenv("APIM_ENV", "internal-dev")
APIM_BASE_URL = f"https://{APIM_ENV}.api.service.nhs.uk"
APIM_ID_BASE_URL = f"https://identity.ptl.api.platform.nhs.uk/realms/NHS-Login-mock-{APIM_ENV}"
logger = logging.getLogger(__name__)


@dataclass
class OAuthClient:
    client_id: str
    client_secret: str
    redirect_uri: str


@dataclass
class ClientCredentials:
    cis2: OAuthClient
    nhs_login: OAuthClient

    @classmethod
    def from_dict(cls, data: dict) -> 'ClientCredentials':
        return cls(
            cis2=OAuthClient(**data['cis2']),
            nhs_login=OAuthClient(**data['nhs-login'])
        )


def init_logging():
    """Initialize logging configuration for debugging HTTP requests."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    if log_level == "TRACE":
        import http.client as http_client
        http_client.HTTPConnection.debuglevel = 1
        logging.basicConfig(level=logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True
    elif log_level == "DEBUG":
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=getattr(logging, log_level, logging.INFO))


def _get_client_creds(base_url: str, api_key: str) -> ClientCredentials:
    print("\n" + "="*80)
    print("STEP 1: Get Client Credentials")
    print("="*80 + "\n")

    url = f"{base_url}/mock-jwks/keycloak-client-credentials"
    headers = {"apikey": api_key}

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    print("✅ Client credentials retrieved")
    json = response.json()
    logger.debug("\n"+"\n".join(f"  {key}: {value}" for key, value in json.items()))
    return ClientCredentials.from_dict(json)


def _authorize(apim_id_base_url: str, client_creds: ClientCredentials) -> str:
    print("\n" + "="*80)
    print("STEPS 3 & 4 (step 2 does not apply): Authorize User")
    print("="*80 + "\n")

    client_id = client_creds.nhs_login.client_id
    scope = "openid%20delegated"
    auth_url = (
        f"{apim_id_base_url}/protocol/openid-connect/auth?scope={scope}&response_type=code"
        f"&client_id={client_id}&redirect_uri=https://google.com"
    )

    print(f"Please visit the following URL to authenticate (example username: 9912003072)\n{auth_url}\n")
    response_code = input("Enter the code param from the resulting URL after authentication: ").strip()

    print(f"✅ Authorization code received: {response_code}")
    return response_code


def _get_id_token(apim_id_base_url: str, client_creds, code) -> str:
    print("\n" + "="*80)
    print("STEP 5: Get ID Token")
    print("="*80 + "\n")

    token_url = f"{apim_id_base_url}/protocol/openid-connect/token"
    client_id = client_creds.nhs_login.client_id
    client_secret = client_creds.nhs_login.client_secret
    # KOP108 step 1 currently returns example.org as redirect uri
    # redirect_uri = client_creds.nhs_login.redirect_uri
    redirect_uri = "https://google.com"

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    logger.debug(f"Requesting ID token from {token_url} with data: {data}")
    response = requests.post(token_url, data=data)
    response.raise_for_status()

    token_response = response.json()
    id_token = token_response.get("id_token")
    print(f"✅ Id Token: {id_token}")
    return id_token


def _get_client_assertion_jwt(apim_base_url: str, kid: str, api_key: str) -> str:
    print("\n" + "="*80)
    print("STEP 6: Get Client Assertion JWT")
    print("="*80 + "\n")

    # Load private key from file
    private_key_path = os.path.join(os.environ["HOME"], ".ssh", f"{kid}.pem")
    if not os.path.isfile(private_key_path):
        raise FileNotFoundError(f"❌ Please provide private key file at {private_key_path}")
    with open(private_key_path, "rb") as key_file:
        private_key = key_file.read()

    # Create JWT Payload
    issued_at = int(time.time())
    expiration = issued_at + 300  # Token valid for 5 minutes
    payload = {
        "iss": api_key,
        "sub": api_key,
        "aud": f"{apim_base_url}/oauth2-mock/token",
        "jti": str(uuid.uuid4()),
        "exp": expiration,
    }

    logger.debug(f"Encoding JWT for application {kid}...")
    headers = {"alg": "RS512", "typ": "JWT", "kid": kid}
    token = jwt.encode(payload, private_key, algorithm="RS512", headers=headers)
    print(f"✅ client_assertion JWT: {token}")
    return token


def _get_access_token(apim_base_url, id_token, client_assert):
    print("\n" + "="*80)
    print("STEP 7: Get Access Token")
    print("="*80 + "\n")

    token_url = f"{apim_base_url}/oauth2-mock/token"

    data = {
        "subject_token": id_token,
        "subject_token_type": "urn:ietf:params:oauth:token-type:id_token",
        "client_assertion": client_assert,
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange"
    }

    logger.debug(f"Requesting access token from {token_url}")
    response = requests.post(token_url, data=data)
    response.raise_for_status()

    token_response = response.json()
    access_token = token_response.get("access_token")
    print(f"✅ Access Token: {access_token}\n")
    return access_token


def main():
    init_logging()

    KID = os.environ.get("KID")
    if not KID:
        raise ValueError("❌ Please set KID environment variable.")
    API_KEY = os.environ.get("API_KEY")
    if not API_KEY:
        raise ValueError("❌ Please set API_KEY environment variable.")

    try:
        client_creds = _get_client_creds(APIM_BASE_URL, API_KEY)  # KOP108 step 1
        # step 2 (OpenId Connect through mock auth server) does not apply
        code = _authorize(APIM_ID_BASE_URL, client_creds)  # KOP108 step 3 & 4
        id_token = _get_id_token(APIM_ID_BASE_URL, client_creds, code)  # KOP108 step 5
        client_assert = _get_client_assertion_jwt(APIM_BASE_URL, KID, API_KEY)  # KOP108 step 6
        _get_access_token(APIM_BASE_URL, id_token, client_assert)  # KOP108 step 7
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error occurred: {e.response.status_code} - {e.response.text}")


if __name__ == "__main__":
    main()
