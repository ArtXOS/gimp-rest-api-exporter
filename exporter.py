#! /usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import os
import gimp
import gimpplugin
from gimpenums import *
import gimpui
import gimpcolor
import pygtk
from gimpshelf import shelf
from gimpfu import *

pdb = gimp.pdb
pygtk.require('2.0')

import gtk

CELL_WIDTH = 200
CELL_HEIGHT = 30
SCROLLED_WINDOW_WIDTH = 600
SCROLLED_WINDOW_HEIGHT = 400
COLUMN_SPACINGS = 10
ROW_SPACINGS = 10
WINDOW_BORDER_WIDTH = 10


class User:
    __authorization = None

    def __init__(self, username, email):
        self.__username = username
        self.__email = email

    def set_authorization(self, authorization):
        self.__authorization = authorization

    def get_authorization(self):
        return self.__authorization

    def get_username(self):
        return self.__username

    def get_email(self):
        return self.__email


class ResponseStatus:
    messages = {
        200: "[200] OK",
        201: "[201] Created",
        400: "[400] Bad request",
        401: "[401] Unauthorized",
        403: "[403] Forbidden",
        404: "[404] Not found",
        504: "[504] Timeout",
        522: "[522] Timeout",
        1000: "Connection refused",
        2000: "ReadTimeout"
    }
    code = None
    message = None

    def __init__(self, code):
        self.code = code
        self.message = ResponseStatus.messages[code]
        if not self.message:
            self.message = "Status [%s]" % code


class Response:
    response_status = None
    headers = None
    payload = None

    def __init__(self, response_status, headers, payload):
        self.response_status = response_status
        self.headers = headers
        self.payload = payload

    pass


class Request:
    method = None
    endpoint = None
    headers = None
    payload = None

    def __init__(self, method, endpoint, headers, payload):
        self.method = method
        self.endpoint = endpoint
        self.headers = headers
        self.payload = payload


class API:
    __host = None

    def __init__(self, host, user):
        self.__host = host
        self.__user = user

    def __method(self, method):
        methods = {
            "GET": self.__get,
            "POST": self.__post,
            "PUT": self.__put,
            "DELETE": self.__delete
        }
        return methods[method]

    def get_host(self):
        return self.__host

    def get_user(self):
        return self.__user

    def do_request(self, request):
        request.headers.update(self.__user.get_authorization())
        try:
            response = self.__method(request.method)(request)
        except requests.exceptions.ConnectionError:
            return Response(ResponseStatus(1000), {}, bytes())
        except requests.exceptions.ReadTimeout:
            return Response(ResponseStatus(2000), {}, bytes())

        return Response(ResponseStatus(response.status_code), response.headers, response.content)

    def __get(self, request):
        response = requests.get(self.__host + request.endpoint, headers=request.headers, timeout=30)
        return response

    def __post(self, request):
        response = requests.post(self.__host + request.endpoint, headers=request.headers, data=request.payload,
                                 timeout=30)
        return response

    def __put(self, request):
        response = requests.put(self.__host + request.endpoint, headers=request.headers, data=request.payload,
                                timeout=30)
        return response

    def __delete(self, request):
        response = requests.delete(self.__host + request.endpoint, headers=request.headers, timeout=30)
        return response

    def check_connection(self):
        response = self.do_request(Request("GET", "", {}, {}))
        if response.response_status.code < 600:
            return "Connected successfully"
        else:
            return "Connection refused"


class Exporter_Window:
    api = None
    user = None

    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("API exporter")
        self.window.connect("delete_event", self.delete_event)
        self.window.set_border_width(WINDOW_BORDER_WIDTH)

        self.layout_table = gtk.Table(10, 6, False)
        self.layout_table.set_row_spacings(ROW_SPACINGS)
        self.layout_table.set_col_spacings(COLUMN_SPACINGS)
        self.window.add(self.layout_table)

        self.widgets_setup()
        self.layout_table_setup()

        self.window.show_all()

    def widgets_setup(self):
        self.username_label = gtk.Label("Username:")
        self.username_entry = gtk.Entry()
        self.username_entry.set_size_request(CELL_WIDTH, CELL_HEIGHT)

        self.email_label = gtk.Label("Email:")
        self.email_entry = gtk.Entry()
        self.email_entry.set_size_request(CELL_WIDTH, CELL_HEIGHT)

        self.token_label = gtk.Label("Token:")
        self.token_entry = gtk.Entry()

        self.host_label = gtk.Label("Host:")
        self.host_entry = gtk.Entry()

        self.connect_button = gtk.Button("Connect")
        self.connect_button.connect("clicked", self.connect_on_click, "Connect")

        self.endpoint_label = gtk.Label("Endpoint:")
        self.endpoint_entry = gtk.Entry()

        self.status_label = gtk.Label("Status:")
        self.status_info = gtk.Label("")

        self.scrolled_window = gtk.ScrolledWindow()
        self.scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolled_window.set_size_request(SCROLLED_WINDOW_WIDTH, SCROLLED_WINDOW_HEIGHT)
        self.scrolled_window.add(self.text_panel)

        self.current_layer_button = gtk.RadioButton(None, "Only current layer")
        self.current_layer_button.connect("toggled", self.empty_callback, "Only current layer")

        self.whole_bitmap_button = gtk.RadioButton(self.current_layer_button, "Whole bitmap")
        self.whole_bitmap_button.connect("toggled", self.empty_callback, "Whole bitmap")

        self.file_format_label = gtk.Label("Format:")

        self.png_button = gtk.RadioButton(None, "PNG")
        self.png_button.connect("toggled", self.empty_callback, "Only current layer")

        self.jpg_button = gtk.RadioButton(self.png_button, "JPG")
        self.jpg_button.connect("toggled", self.empty_callback, "Whole bitmap")

        self.export_button = gtk.Button("Export")
        self.export_button.connect("clicked", self.export_on_click, "Export")

        self.export_as_entry = gtk.Entry()
        self.export_as_entry.set_text("Enter the name")

        self.text_panel = gtk.TextView()
        self.textbuffer = self.text_panel.get_buffer()

    def layout_table_setup(self):
        self.layout_table.attach(self.username_label, 0, 1, 0, 1)
        self.layout_table.attach(self.username_entry, 1, 3, 0, 1)

        self.layout_table.attach(self.email_label, 3, 4, 0, 1)
        self.layout_table.attach(self.email_entry, 4, 6, 0, 1)

        self.layout_table.attach(self.token_label, 0, 1, 1, 2)
        self.layout_table.attach(self.token_entry, 1, 3, 1, 2)

        self.layout_table.attach(self.host_label, 3, 4, 1, 2)
        self.layout_table.attach(self.host_entry, 4, 6, 1, 2)

        self.layout_table.attach(self.connect_button, 0, 3, 2, 3)

        self.layout_table.attach(self.endpoint_label, 0, 1, 3, 4)
        self.layout_table.attach(self.endpoint_entry, 1, 4, 3, 4)

        self.layout_table.attach(self.status_label, 4, 5, 3, 4)
        self.layout_table.attach(self.status_info, 5, 6, 3, 4)

        self.layout_table.attach(self.scrolled_window, 0, 6, 4, 8)

        self.layout_table.attach(self.current_layer_button, 0, 1, 8, 9)
        self.layout_table.attach(self.whole_bitmap_button, 1, 2, 8, 9)

        self.layout_table.attach(self.file_format_label, 3, 4, 8, 9)

        self.layout_table.attach(self.png_button, 4, 5, 8, 9)
        self.layout_table.attach(self.jpg_button, 5, 6, 8, 9)

        self.layout_table.attach(self.export_button, 0, 1, 9, 10)
        self.layout_table.attach(self.export_as_entry, 1, 6, 9, 10)

    def set_image(self, image):
        self.image = image

    def set_drawable(self, drawable):
        self.drawable = drawable

    def valid_api(self):
        if self.api is None or self.api.get_host() is None:
            return False

        host = self.api.get_host().lower()

        if not host.startswith("http://") and not host.startswith("https://"):
            self.textbuffer.set_text("Host name should start with \"http://\" or \"https://")
            return False

        return True

    def delete_event(self, widget, event, data=None):
        gtk.main_quit()
        return False

    def empty_callback(self, widget, event):
        pass

    def connect_on_click(self, widget, event):
        username = self.username_entry.get_text()
        user_email = self.email_entry.get_text()
        user_token = self.token_entry.get_text()
        host = self.host_entry.get_text()

        self.user = User(username, user_email)
        self.user.set_authorization({"Authorization": "Bearer " + user_token})

        self.api = API(host, self.user)

        if not self.valid_api():
            return

        connection_status = self.api.check_connection()
        self.status_info.set_text(connection_status)

    def export_on_click(self, widget, event):
        if not self.valid_api():
            self.textbuffer.set_text("Please, connect first")
            return

        file_name = self.export_as_entry.get_text()

        if not file_name:
            self.textbuffer.set_text("File name is empty")
            return

        file_format = ".png" if self.png_button.get_active() else ".jpg"
        file_name = file_name + file_format

        if self.current_layer_button.get_active():
            pdb.gimp_file_save(self.image, self.drawable, file_name, '?')
        elif self.whole_bitmap_button.get_active():
            new_image = pdb.gimp_image_duplicate(self.image)
            new_image.flatten()
            pdb.gimp_file_save(new_image, new_image.layers[0], file_name, '?')
            pdb.gimp_image_delete(new_image)

        self.textbuffer.set_text("Exporting... " + file_name)

        endpoint = self.endpoint_entry.get_text()
        headers = {"Content-Type": "multipart/form-data"}
        file = open(file_name, "rb")
        payload = {"texture": (file_name, file)}

        request = Request("POST", endpoint, headers, payload)
        response = self.api.do_request(request)

        file.close()
        os.remove(file_name)

        payload = response.payload
        self.textbuffer.set_text(payload)
        self.status_info.set_text(response.response_status.message)


class GimpExporter(gimpplugin.plugin):
    def start(self):
        gimp.main(self.init, self.quit, self.query, self._run)

    def init(self):
        pass

    def quit(self):
        pass

    def query(self):
        gimp.install_procedure(
            "export_to_api",
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

    def export_to_api(self, run_mode, image, drawable):
        self.image = image
        self.drawable = drawable
        gimp.pdb.gimp_image_undo_group_start(self.image)

        self.window = Exporter_Window()
        self.window.set_drawable(self.drawable)
        self.window.set_image(self.image)
        gtk.main()

        gimp.pdb.gimp_image_undo_group_end(self.image)


if __name__ == "__main__":
    exporter = GimpExporter()
    exporter.start()
