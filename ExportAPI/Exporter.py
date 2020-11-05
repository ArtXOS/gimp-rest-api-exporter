from abc import ABC, abstractmethod


class Exporter(ABC):

    __exporter_name: str

    @abstractmethod
    def get_exporter_name(self):
        pass


def main():
    pass


if __name__ == "__main__":
    main()
