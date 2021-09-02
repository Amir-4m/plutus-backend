import hashlib
import struct
import uuid
from rest_framework.exceptions import ErrorDetail
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    if response and isinstance(response.data, list):
        return response

    if response is not None and 'detail' not in response.data:
        err = ''
        for k in exc.detail.keys():
            v = exc.detail[k]
            if isinstance(v, list):
                v = v[0]

            err = str(v)
            if isinstance(v, ErrorDetail):
                if k != 'non_field_errors':
                    err = f'{k}, {v}'
            if err:
                break
        response.data['detail'] = err
    elif response is not None and isinstance(response.data['detail'], list):
        response.data['detail'] = response.data['detail'][0]

    return response
