import os
from pinthesky.auth import user_jwt
from requests import exceptions
from unittest import mock


ENDPOINT = 'https://cognito-idp.us-east-2.amazonaws.com/efg-456/.well-known/jwks.json'
FAKE_TOKEN = "eyJraWQiOiJIRWJFMXRSdWZSMngzYzVCN3NrbmVcL2ZmRlhlRitTY25MdlVSXC9COGpHemc9IiwiYWxnIjoiUlMyNTYifQ.eyJhdF9oYXNoIjoiTnN1ZFpvQ3BjZEQ2SExxcGxGbnBNZyIsInN1YiI6Ijk4NDk4MDc3LTRjMWQtNGZmYi1hYjNkLTg1MzJkY2U1ZGI0ZCIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAudXMtZWFzdC0xLmFtYXpvbmF3cy5jb21cL3VzLWVhc3QtMV9kSHpVQ3hzWXMiLCJjb2duaXRvOnVzZXJuYW1lIjoicGhpbGNhbGkiLCJhdWQiOiIyN3BrM2FvaWEybDM0N29xN3NpMHY4ajNtYiIsImV2ZW50X2lkIjoiZjJjNThmNmQtM2JjNS00NWVkLThhMDQtODg1ZDdmNjg1ZjY2IiwidG9rZW5fdXNlIjoiaWQiLCJhdXRoX3RpbWUiOjE3MTE2NjEzMTIsImV4cCI6MTcxMTc0NzcxMiwiaWF0IjoxNzExNjYxMzEyLCJqdGkiOiIzOTI0NTk3YS02N2YxLTQwNjItYjUxOS1lOWJjZmM0YjhlNmIiLCJlbWFpbCI6InBoaWxpcC5jYWxpQGdtYWlsLmNvbSJ9.PGlCjHGq0bZFs8eIunB0BRvo2QUPZhxRmBOOqZ3E-wdCkFTq7uLRTxaoPmKQQlwRyF4Ht3d-bNb3mu8PmGAr397JyfB4akqJ-zL6yPeWXZvUsTAADOE_xzLfe2jJgLCK3B6TCi2AFNB9tleu-M_Ri63pgtTZ9RCCiO7pTLA-3iXrqVlb_K6uq8GREzHLKePu7yt5-wa8omgPhjGRndahlhHpUwqoix3yJCe8lDYY6965Bcb18dd3bxFtTLagXAjGt8zGQC6jiBOxTTWX23TbzfQh8l5Pry0gfGwoabM2OJvSJtjMftBzP4vQCawE6-3JBEsd2At-rmBJzvSMKg4TBw"
FAKE_KEYS = {
    "keys": [
        {
            "alg": "RS256",
            "e": "AQAB",
            "kid": "HEbE1tRufR2x3c5B7skne/ffFXeF+ScnLvUR/B8jGzg=",
            "kty": "RSA",
            "n": "u5fzT1DIa20hVMELN4EURTRe0HEc2ZA65ILXGNOoNyw3SEWki_ZnzgtpxQUp51Hg4ZG0yew6uOUf_KjEcMAv4BdSBl3XXsrE3SIaMStT15zx5bKI_CVgboeo6usnieg3aDFMygJBx-HVKMr6V7oQxR8RcNMA-8NcnfyHL1ZuspYQl-rPDguxB2s4K0qK3grEXi8BIsPVlJ_KtaYCHzLGrwJaB5ZX1PDw5DrG4b89Nvi4WCHMkBJxlCIuY0Iq_ROKUVtWZhR9cuTy9bK4HiF_Sy7uR-G-3z9YPRQ0VKoF9ZXxIJfO1YR8W6PwWi1MR0Yo-Mg8Zk-LYYm_UsutONvifQ",
            "use": "sig"
        },
        {
            "alg": "RS256",
            "e": "AQAB",
            "kid": "bDCwUwBooN9S4OoogoiMaQvUFpfJdjlVsnwHQd5dsGQ=",
            "kty": "RSA",
            "n": "3_paFrvTopeNeUkHrEayF9e78FDZ6nFlRg1J_TcVJyn8Ye5KalR0ElBKhcRn59fBNMOAi1yN49j0-ITZ7noWuNfU1nNp_vYdJrx17e2t1cJZ-Yd3TtLHs1Sury0ZTKX9pbkoxANisiOYW-r5CSuQGBJH-AmNX_SxsutnaYuvluY4GiBCo-hvv_dbk9HWYionVZL2PgOfAGlpqdoCo-nhKyJ0Pn9PlGKoI_HDL1rV-fx3XjnpXChsyvoIxkhwDy6WmU4zKXb1kaZ7L_A-gC9cFiEAkOTRukrWRTEBgKtifq57MLLVVkMKhIYgduOQSsuOD1TMw6vgKUYw-0YSFkB__w",
            "use": "sig"
        }
    ]
}


def test_no_header():
    policy = user_jwt({
        'headers': {
            'Content-Length': 0,
        },
        'requestContext': {
            'connectionId': 'abc-123',
        },
        'queryStringParameters': {
        },
        'methodArn': '$connect',
    }, None)
    assert policy == {
        'principalId': 'abc-123',
        'policyDocument': {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': 'execute-api:Invoke',
                    'Resource': '$connect',
                }
            ]
        },
        'context': {
        }
    }


def test_fail_key_retrieval(requests_mock):
    requests_mock.get(ENDPOINT, exc=exceptions.ConnectTimeout)
    os.environ['AWS_REGION'] = 'us-east-2'
    os.environ['USER_POOL_ID'] = 'efg-456'
    policy = user_jwt({
        'headers': {
            'Content-Length': 0,
        },
        'requestContext': {
            'connectionId': 'abc-123',
        },
        'queryStringParameters': {
            'Authorization': FAKE_TOKEN,
        },
        'methodArn': '$connect',
    }, None)
    assert policy == {
        'principalId': 'abc-123',
        'policyDocument': {
            'Statement': [
                {
                    'Effect': 'Deny',
                    'Action': 'execute-api:Invoke',
                    'Resource': '$connect',
                }
            ]
        },
        'context': {
        }
    }


def test_fail_invalid_key(requests_mock):
    requests_mock.get(ENDPOINT, json={
        'keys': [
            {
                "alg": "RS256",
                "e": "AQAB",
                "kid": "hack/hack/hack",
                "kty": "RSA",
                "n": "hack/hack/hack",
                "use": "sig"
            },
        ]
    })
    os.environ['AWS_REGION'] = 'us-east-2'
    os.environ['USER_POOL_ID'] = 'efg-456'
    policy = user_jwt({
        'headers': {
            'Content-Length': 0,
            'Authorization': FAKE_TOKEN,
        },
        'requestContext': {
            'connectionId': 'abc-123',
        },
        'queryStringParameters': {
        },
        'methodArn': '$connect',
    }, None)
    assert policy == {
        'principalId': 'abc-123',
        'policyDocument': {
            'Statement': [
                {
                    'Effect': 'Deny',
                    'Action': 'execute-api:Invoke',
                    'Resource': '$connect',
                }
            ]
        },
        'context': {
        }
    }


def test_fail_invalid_signature(requests_mock):
    fake_algos = {
        'keys': [
            {
                **FAKE_KEYS['keys'][0],
                'n': 'aGFjay9oYWNrL2hhY2s=',
            },
            {
                **FAKE_KEYS['keys'][1],
                'n': 'aGFjay9oYWNrL2hhY2s=',
            }
        ]
    }
    requests_mock.get(ENDPOINT, json=fake_algos)
    os.environ['AWS_REGION'] = 'us-east-2'
    os.environ['USER_POOL_ID'] = 'efg-456'
    policy = user_jwt({
        'headers': {
            'Content-Length': 0,
            'Authorization': FAKE_TOKEN,
        },
        'requestContext': {
            'connectionId': 'abc-123',
        },
        'queryStringParameters': {
        },
        'methodArn': '$connect',
    }, None)
    assert policy == {
        'principalId': 'abc-123',
        'policyDocument': {
            'Statement': [
                {
                    'Effect': 'Deny',
                    'Action': 'execute-api:Invoke',
                    'Resource': '$connect',
                }
            ]
        },
        'context': {
        }
    }


def test_fail_expired(requests_mock):
    requests_mock.get(ENDPOINT, json=FAKE_KEYS)
    os.environ['AWS_REGION'] = 'us-east-2'
    os.environ['USER_POOL_ID'] = 'efg-456'
    policy = user_jwt({
        'headers': {
            'Content-Length': 0,
            'Authorization': FAKE_TOKEN,
        },
        'requestContext': {
            'connectionId': 'abc-123',
        },
        'queryStringParameters': {
        },
        'methodArn': '$connect',
    }, None)
    assert policy == {
        'principalId': 'abc-123',
        'policyDocument': {
            'Statement': [
                {
                    'Effect': 'Deny',
                    'Action': 'execute-api:Invoke',
                    'Resource': '$connect',
                }
            ]
        },
        'context': {
        }
    }


@mock.patch('time.time', mock.MagicMock(return_value=1711747711))
def test_failed_invalid_audience(requests_mock):
    requests_mock.get(ENDPOINT, json=FAKE_KEYS)
    os.environ['AWS_REGION'] = 'us-east-2'
    os.environ['USER_POOL_ID'] = 'efg-456'
    os.environ['USER_CLIENT_ID'] = 'hack/hack/hack'
    policy = user_jwt({
        'headers': {
            'Content-Length': 0,
            'Authorization': FAKE_TOKEN,
        },
        'requestContext': {
            'connectionId': 'abc-123',
        },
        'queryStringParameters': {
        },
        'methodArn': '$connect',
    }, None)
    assert policy == {
        'principalId': 'abc-123',
        'policyDocument': {
            'Statement': [
                {
                    'Effect': 'Deny',
                    'Action': 'execute-api:Invoke',
                    'Resource': '$connect',
                }
            ]
        },
        'context': {
        }
    }


@mock.patch('time.time', mock.MagicMock(return_value=1711747711))
def test_allow(requests_mock):
    requests_mock.get(ENDPOINT, json=FAKE_KEYS)
    os.environ['AWS_REGION'] = 'us-east-2'
    os.environ['USER_POOL_ID'] = 'efg-456'
    os.environ['USER_CLIENT_ID'] = '27pk3aoia2l347oq7si0v8j3mb'
    policy = user_jwt({
        'headers': {
            'Content-Length': 0,
            'Authorization': FAKE_TOKEN,
        },
        'requestContext': {
            'connectionId': 'abc-123',
        },
        'queryStringParameters': {
        },
        'methodArn': '$connect',
    }, None)
    assert policy == {
        'principalId': 'abc-123',
        'policyDocument': {
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': 'execute-api:Invoke',
                    'Resource': '$connect',
                }
            ]
        },
        'context': {
            "at_hash": "NsudZoCpcdD6HLqplFnpMg",
            "sub": "98498077-4c1d-4ffb-ab3d-8532dce5db4d",
            "email_verified": True,
            "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_dHzUCxsYs",
            "cognito:username": "philcali",
            "aud": "27pk3aoia2l347oq7si0v8j3mb",
            "event_id": "f2c58f6d-3bc5-45ed-8a04-885d7f685f66",
            "token_use": "id",
            "auth_time": 1711661312,
            "exp": 1711747712,
            "iat": 1711661312,
            "jti": "3924597a-67f1-4062-b519-e9bcfc4b8e6b",
            "email": "philip.cali@gmail.com"
        }
    }
