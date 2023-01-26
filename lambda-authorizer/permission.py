# # Native # #
import os
import json
import requests

# # Installed # #

# # Package # #
from logger import logger
from exceptions import ForbiddenException, UnauthorizedException
from utils import get_lambda_client


__all__ = (
    'user_validate',
    'rbac_validate',
    'visibility_group_validate',
)


def user_validate(access_token, email, communication):
    """Validate user permissions for the current user."""
    if not access_token:
        raise UnauthorizedException
    if communication == 'api':

        if not os.environ['APP_BASE_URL']:
            raise ForbiddenException(
                detail='APP_BASE_URL not set, will not continue')

        response = requests.get(
            url='%s/api/auth/v1/user/list?page=1&size=1&filters={"email": "%s"}' % (
                os.getenv("APP_BASE_URL"), email),
            headers={'Authorization': access_token}
        )
        logger.info(
            f"/user/list response_status: {response.status_code}; response: {response.text}")
        if response.status_code == 200:
            return response.json()['data']['items']
        else:
            raise ForbiddenException(detail=response.text)

    elif communication == 'lambda':

        if not os.environ['APP_FUNCTION_ARN']:
            raise ForbiddenException(
                detail='APP_FUNCTION_ARN not set, will not continue')

        client = get_lambda_client()
        payload = {
            'resource': '/api/auth/v1/{proxy+}',
            'path': '/api/auth/v1/user/list',
            'queryStringParameters': {
                'page': '1',
                'size': '1',
                'filters': '{"email": "%s"}' % email
            },
            'headers': {'Authorization': access_token},
            'httpMethod': 'GET',
            'requestContext': {}
        }
        logger.info(f"payload: {payload}")
        response = client.invoke(
            FunctionName=os.environ['APP_FUNCTION_ARN'],
            InvocationType='RequestResponse',
            Payload=bytes(json.dumps(payload), 'utf-8'),
        )

        lambda_status_code = response['StatusCode']
        if lambda_status_code != 200:
            raise ForbiddenException(detail="Lambda error")
        response = json.loads(response['Payload'].read())
        status_code = response['statusCode']
        response = json.loads(response['body'])
        logger.info(f"/user/list response: {response}")

        if isinstance(response, dict) and 'error' in response.keys():
            raise ForbiddenException(detail=response)

        if status_code == 200:
            return response['data']['items']
        else:
            raise ForbiddenException(detail=response)


def rbac_validate(request, communication):
    """Validate RBAC permissions for the current request."""

    data = {
        'endpoint': request.resource,
        'method': request.httpMethod
    }
    access_token = request.headers.get('authorization') or request.headers.get('Authorization')
    if not access_token:
        raise ForbiddenException(detail="No Authorization header found")

    if communication == 'api':

        if not os.environ['APP_BASE_URL']:
            raise ForbiddenException(
                detail='APP_BASE_URL not set, will not continue')

        response = requests.post(
            url=f'{os.getenv("APP_BASE_URL")}/api/auth/v1/rbac/validate', headers={'Authorization': access_token}, json=data)
        logger.info(
            f"/rbac/validate response_status: {response.status_code}; response: {response.text}")
        if response.status_code == 200:
            if not response.json()['data']['access']:
                raise ForbiddenException
        elif response.status_code == 401:
            raise UnauthorizedException
        else:
            raise ForbiddenException

    elif communication == 'lambda':

        if not os.environ['APP_FUNCTION_ARN']:
            raise ForbiddenException(
                detail='APP_FUNCTION_ARN not set, will not continue')

        client = get_lambda_client()

        payload = {
            'resource': '/api/auth/v1/{proxy+}',
            'path': '/api/auth/v1/rbac/validate',
            'httpMethod': 'POST',
            'headers': {'Authorization': access_token},
            'body': json.dumps(data),
            'requestContext': {}
        }

        response = client.invoke(
            FunctionName=os.environ['APP_FUNCTION_ARN'],
            InvocationType='RequestResponse',
            Payload=bytes(json.dumps(payload), 'utf-8'),
        )

        lambda_status_code = response['StatusCode']
        if lambda_status_code != 200:
            raise ForbiddenException
        response = json.loads(response['Payload'].read())
        logger.info(
            f"/rbac/validate response: {response}")
        status_code = response['statusCode']
        response = json.loads(response['body'])

        if isinstance(response, dict) and 'error' in response.keys():
            raise ForbiddenException

        if status_code == 200:
            if not response['data']['access']:
                raise ForbiddenException
        elif status_code == 401:
            raise UnauthorizedException
        else:
            raise ForbiddenException


def visibility_group_validate(access_token, visibility_group_entity, communication):
    """Validate visibility group permissions for the current user."""
    if not access_token:
        raise UnauthorizedException
    if communication == 'api':
        if not os.environ['APP_BASE_URL']:
            raise ForbiddenException(
                detail='APP_BASE_URL not set, will not continue')

        response = requests.get(
            url=f'{os.getenv("APP_BASE_URL")}/api/auth/v1/visibility_group/validate/{visibility_group_entity}', headers={'Authorization': access_token})
        logger.info(
            f"/visibility_group/validate response_status: {response.status_code}; response: {response.text}")
        if response.status_code == 200:
            return response.json()
        else:
            raise ForbiddenException

    elif communication == 'lambda':
        if not os.environ['APP_FUNCTION_ARN']:
            raise ForbiddenException(
                detail='APP_FUNCTION_ARN not set, will not continue')

        client = get_lambda_client()
        payload = {
            'resource': '/api/auth/v1/{proxy+}',
            'path': f'/api/auth/v1/visibility_group/validate/{visibility_group_entity}',
            'httpMethod': 'GET',
            'headers': {'Authorization': access_token},
            'requestContext': {}
        }
        response = client.invoke(
            FunctionName=os.environ['APP_FUNCTION_ARN'],
            InvocationType='RequestResponse',
            Payload=bytes(json.dumps(payload), 'utf-8'),
        )

        lambda_status_code = response['StatusCode']
        if lambda_status_code != 200:
            raise ForbiddenException
        response = json.loads(response['Payload'].read())
        logger.info(f"/visibility_group/validate response: {response}")
        status_code = response['statusCode']
        response = json.loads(response['body'])
        if isinstance(response, dict) and 'error' in response.keys():
            raise ForbiddenException

        if status_code == 200:
            return response
        else:
            raise ForbiddenException
