# TODO Authorization Type class

class User:

    __authorization = ""

    def __init__(self, username: str, email: str):
        self.__username = username
        self.__email = email

    def set_authorization(self, authorization: str):
        self.__authorization = authorization

    def get_authorization(self) -> str:
        return self.__authorization

    def get_username(self) -> str:
        return self.__username

    def get_email(self) -> str:
        return self.__email


def main():
    pass


if __name__ == "__main__":
    main()
