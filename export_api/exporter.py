from abc import ABC, abstractmethod


class Exporter(ABC):

    exporter_info: dict
    api: object

    @abstractmethod
    def get_exporter_name(self):
        pass

    @abstractmethod
    def start(self):
        pass




if __name__ == "__main__":
    main()
