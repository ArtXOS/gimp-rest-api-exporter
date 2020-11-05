from ExportAPI.Exporter import Exporter
from ExportAPI.User import User
import requests
import json


class ResponseStatus:
    messages = {
        200: "[200] OK",
        201: "[201] Created",
        400: "[400] Bad request",
        401: "[401] Unauthorized",
        403: "[403] Forbidden",
        404: "[404] Not found",
        504: "[504] Timeout",
        522: "[522] Timeout"
    }
    code: int
    message = ""

    def __init__(self, code: int):
        self.code = code
        self.message = ResponseStatus.messages[code]
        if not self.message:
            self.message = f"Status [{code}]"


class Response:
    response_status: ResponseStatus
    headers: dict
    payload: bytes

    def __init__(self, response_status: ResponseStatus, headers: dict, payload: bytes):
        self.response_status = response_status
        self.headers = headers
        self.payload = payload
        if response_status.code not in range(200, 299):
            response_status.message += "\nResponse Content:\n" + str(payload)

    pass


class Request:
    method: str
    endpoint: str
    headers: dict
    payload: {}

    def __init__(self, method: str, endpoint: str, headers: dict, payload):
        self.method = method
        self.endpoint = endpoint
        self.headers = headers
        self.payload = payload

    pass


class API:

    def __init__(self, address: str, user: User):
        self.__address = address
        self.__user = user

    def __method(self, method: str):
        methods = {
            "GET": self.__get,
            "POST": self.__post,
            "PUT": self.__put,
            "DELETE": self.__delete
        }
        return methods[method]

    def get_address(self) -> str:
        return self.__address

    def get_user(self) -> User:
        return self.__user

    def do_request(self, request: Request) -> Response:
        request.headers.update({"Authorization": self.__user.get_authorization()})
        response = self.__method(request.method)(request)
        return Response(ResponseStatus(response.status_code), dict(response.headers), response.content)

    def __get(self, request: Request) -> requests.Response:
        response = requests.get(self.__address + request.endpoint, headers=request.headers, timeout=10)
        return response

    def __post(self, request: Request) -> requests.Response:
        response = requests.post(self.__address + request.endpoint, headers=request.headers, data="", timeout=30)
        return response

    def __put(self, request: Request) -> requests.Response:
        response = requests.put(self.__address + request.endpoint, headers=request.headers, data="", timeout=30)
        return response

    def __delete(self, request: Request) -> requests.Response:
        response = requests.delete(self.__address + request.endpoint, headers=request.headers, data="", timeout=30)
        return response

    def check_connection(self) -> str:
        pass


def main(): pass


if __name__ == "__main__":
    main()
