import gimpplugin
import gtk
import gimpui
from gimpenums import *


class GimpExporter(gimpplugin.plugin):

    action = None
    layer = None

    def start(self):
        gimp.main(self.init, self.quit, self.query, self._run)

    def init(self):
        pass

    def quit(self):
        pass

    def query(self):
        gimp.install_procedure(
            "api_export_plugin",
            "GIMP to API export plugin",
            "Export layer all the whole image to your API.",
            "Illia Brylov",
            "Illia Brylov",
            "2020",
            "<Image>/APIexport",
            "RGB*, GRAY*",
            PLUGIN,
            [  # next three parameters are common for all scripts that are inherited from gimpplugin.plugin
                (PDB_INT32, "run_mode", "Run mode"),
                (PDB_IMAGE, "image", "Input image"),
                (PDB_DRAWABLE, "drawable", "Input drawable"),
            ],
            []
        )

    def get_exporter_name(self):
        pass


if __name__ == "__main__":
    exporter = GimpExporter()
    exporter.start()
