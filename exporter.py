#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Export plugin to REST API for GIMP 2.10.22
    Import section possibly will be added in the nearest future
"""

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

# Table cell settings
CELL_WIDTH = 200
CELL_HEIGHT = 30

# UI scrolled window settings
SCROLLED_WINDOW_WIDTH = 600
SCROLLED_WINDOW_HEIGHT = 400

# Additional UI settings
COLUMN_SPACINGS = 10
ROW_SPACINGS = 10
WINDOW_BORDER_WIDTH = 10

# Export settings
TIMEOUT = 10
EXPORT_HTTP_METHOD = "POST"


# ------------ PLUGIN HELPERS SECTION ------------ #
class User:
    """
        User class to store info about user

        __authorization: User authorization header as dictionary
        __username: username string
        __email: username email string
    """
    __authorization = None
    __username = None
    __email = None

    def __init__(self, username, email):
        self.__username = username
        self.__email = email

    def set_authorization(self, authorization):
        """
        This method is expecting to take a dictionary as an argument
        :param authorization: dictionary with headers
        :return: reference to self
        """
        self.__authorization = authorization
        return self

    def get_authorization(self):
        return self.__authorization

    def get_username(self):
        return self.__username

    def get_email(self):
        return self.__email


class ResponseStatus:
    """
        ResponseStatus helps to interpret HTTP status codes to info messages. You can add additional messages by
        adding a code to messages dictionary

        messages: dictionary of messages for HTTP response codes
        code: HTTP response code
        message: message based on HTTP code
    """
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
        2000: "ReadTimeout",
        3000: "Unknown error"
    }
    code = None
    message = None

    def __init__(self, code):
        """
        If the code number is absent in internal dictionary, the generic message will be assigned
        :param code: HTTP response code
        """
        self.code = code
        self.message = ResponseStatus.messages[code]

        if not self.message:
            self.message = "Status [%s]" % code


class Response:
    """
    Response class is representing HTTP Response. It helps to store all data needed from the response received

    response_status: ResponseStatus object
    header: response headers dictionary
    payload: response body
    """
    response_status = None
    headers = None
    payload = None

    def __init__(self, response_status, headers, payload):
        self.response_status = response_status
        self.headers = headers
        self.payload = payload


class Request:
    """
    Request class is representing HTTP Request. It helps to store all data needed to send the HTTP request

    method: HTTP method to make
    endpoint: API endpoint to send a request to. /textures f.e.
    headers: headers dictionary to send in request
    payload: request body to send to the API. files=payload by default
    """
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
    """
    API class is used to communicate with external API. It has a method to do the Request to receive the Response

    __host: host string https://google.com f.e.
    """
    __host = None

    def __init__(self, host, user):
        self.__host = host
        self.__user = user

    def __method(self, method):
        """
        Private method to return private method of each HTTP method. Used for the Request processing
        :param method: HTTP method as uppercase string
        :return: private method as function object
        """
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
        """
        This method updates Request object headers with User authorization and then calls the HTTP method, based on
        Request object method attribute. Handles possible exceptions. In case of an exception, Response object
        will contain only ResponseStatus with a message about an error
        :param request: Request object filled with data
        :return: Response object filled with data
        """

        request.headers.update(self.__user.get_authorization())

        try:
            response = self.__method(request.method)(request)
        except requests.exceptions.ConnectionError:
            return Response(ResponseStatus(1000), "", "")
        except requests.exceptions.ReadTimeout:
            return Response(ResponseStatus(2000), "", "")
        except Exception:
            return Response(ResponseStatus(3000), "", "")

        return Response(ResponseStatus(response.status_code), response.headers, response.content)

    def __get(self, request):
        response = requests.get(self.__host + request.endpoint, headers=request.headers, timeout=TIMEOUT)
        return response

    def __post(self, request):
        response = requests.post(self.__host + request.endpoint, headers=request.headers, files=request.payload,
                                 timeout=TIMEOUT)
        return response

    def __put(self, request):
        response = requests.put(self.__host + request.endpoint, headers=request.headers, files=request.payload,
                                timeout=TIMEOUT)
        return response

    def __delete(self, request):
        response = requests.delete(self.__host + request.endpoint, headers=request.headers, timeout=TIMEOUT)
        return response

    def check_connection(self):
        """
        Method that checks if there is any response from host
        :return: Connected successfully if there was any response from the host, Connection error if not
        """
        response = self.do_request(Request("GET", "", {}, {}))

        if response.response_status.code < 600:
            return "Connected successfully"
        else:
            return "Connection error"


# ------------ PLUGIN UI AND LOGIC ------------ #

class ExporterWindow:
    """
    Class which defines the plugin UI and implements some callbacks (sort of internal logic)

    api: API object to communicate with
    user: User object
    image: pdb image
    drawable: pdd drawable
    """
    api = None
    user = None
    image = None
    drawable = None

    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("API exporter")
        self.window.connect("delete_event", self.delete_event)
        self.window.set_border_width(WINDOW_BORDER_WIDTH)

        # Plugin layout is Table 10 x 6
        self.layout_table = gtk.Table(7, 6, False)
        self.layout_table.set_row_spacings(ROW_SPACINGS)
        self.layout_table.set_col_spacings(COLUMN_SPACINGS)
        self.window.add(self.layout_table)

        self.widgets_setup()
        self.layout_table_setup()

        self.window.show_all()

    def widgets_setup(self):
        """
        Method that defines each UI widget and its behaviour. In case of changing plugin UI, just change the widget
        here or add another. Don't forget to attach new widget to the layout table in layout_table_setup method.
        If you oftenly same values in entries, just change the default values of them by calling set_text()
        method on them
        :return: None
        """

        # 1 row --------------------------------------
        self.username_label = gtk.Label("Username:")
        self.username_entry = gtk.Entry()
        self.username_entry.set_size_request(CELL_WIDTH, CELL_HEIGHT)

        self.email_label = gtk.Label("Email:")
        self.email_entry = gtk.Entry()
        self.email_entry.set_size_request(CELL_WIDTH, CELL_HEIGHT)

        # 2 row --------------------------------------
        self.token_label = gtk.Label("Token:")
        self.token_entry = gtk.Entry()

        self.host_label = gtk.Label("Host:")
        self.host_entry = gtk.Entry()

        # 3 row --------------------------------------
        self.connect_button = gtk.Button("Connect")
        self.connect_button.connect("clicked", self.connect_on_click, "Connect")

        # 4 row --------------------------------------
        self.endpoint_label = gtk.Label("Endpoint:")
        self.endpoint_entry = gtk.Entry()

        self.status_label = gtk.Label("Status:")
        self.status_info = gtk.Label("")

        # 5 row --------------------------------------
        self.text_panel = gtk.TextView()
        self.textbuffer = self.text_panel.get_buffer()

        self.scrolled_window = gtk.ScrolledWindow()
        self.scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolled_window.set_size_request(SCROLLED_WINDOW_WIDTH, SCROLLED_WINDOW_HEIGHT)
        self.scrolled_window.add(self.text_panel)

        # 6 row --------------------------------------
        self.current_layer_button = gtk.RadioButton(None, "Only current layer")
        self.current_layer_button.connect("toggled", self.empty_callback, "Only current layer")

        self.whole_bitmap_button = gtk.RadioButton(self.current_layer_button, "Whole bitmap")
        self.whole_bitmap_button.connect("toggled", self.empty_callback, "Whole bitmap")

        self.file_format_label = gtk.Label("Format:")

        self.png_button = gtk.RadioButton(None, "PNG")
        self.png_button.connect("toggled", self.empty_callback, "Only current layer")

        self.jpg_button = gtk.RadioButton(self.png_button, "JPG")
        self.jpg_button.connect("toggled", self.empty_callback, "Whole bitmap")

        # 7 row --------------------------------------
        self.export_button = gtk.Button("Export")
        self.export_button.connect("clicked", self.export_on_click, "Export")

        self.export_as_entry = gtk.Entry()
        self.export_as_entry.set_text("Enter the name")

    def layout_table_setup(self):
        """
        Attaches widgets defined in widgets_setup to layout table
        :return: None
        """

        # 1 row --------------------------------------
        self.layout_table.attach(self.username_label, 0, 1, 0, 1)
        self.layout_table.attach(self.username_entry, 1, 3, 0, 1)

        self.layout_table.attach(self.email_label, 3, 4, 0, 1)
        self.layout_table.attach(self.email_entry, 4, 6, 0, 1)

        # 2 row --------------------------------------
        self.layout_table.attach(self.token_label, 0, 1, 1, 2)
        self.layout_table.attach(self.token_entry, 1, 3, 1, 2)

        self.layout_table.attach(self.host_label, 3, 4, 1, 2)
        self.layout_table.attach(self.host_entry, 4, 6, 1, 2)

        # 3 row --------------------------------------
        self.layout_table.attach(self.connect_button, 0, 3, 2, 3)

        # 4 row --------------------------------------
        self.layout_table.attach(self.endpoint_label, 0, 1, 3, 4)
        self.layout_table.attach(self.endpoint_entry, 1, 4, 3, 4)

        self.layout_table.attach(self.status_label, 4, 5, 3, 4)
        self.layout_table.attach(self.status_info, 5, 6, 3, 4)

        # 5 row --------------------------------------
        self.layout_table.attach(self.scrolled_window, 0, 6, 4, 5)

        # 6 row --------------------------------------
        self.layout_table.attach(self.current_layer_button, 0, 1, 5, 6)
        self.layout_table.attach(self.whole_bitmap_button, 1, 2, 5, 6)

        self.layout_table.attach(self.file_format_label, 3, 4, 5, 6)
        self.layout_table.attach(self.png_button, 4, 5, 5, 6)
        self.layout_table.attach(self.jpg_button, 5, 6, 5, 6)

        # 7 row --------------------------------------
        self.layout_table.attach(self.export_button, 0, 1, 6, 7)
        self.layout_table.attach(self.export_as_entry, 1, 6, 6, 7)

    def set_image(self, image):
        self.image = image

    def set_drawable(self, drawable):
        self.drawable = drawable

    def valid_api(self):
        """
        Checking if the api attribute is valid. Prints a message to scrolled window if the api host is in invalid format
        :return: True if valid, otherwise False
        """
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
        """
        Callback of the Connect button to check, if there is any response from the host.
        Uses api's check_connection. Prints the result to scrolled_window
        :param widget: widget
        :param event: event
        :return: None
        """
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
        """
        Export button callback which provides the export of the file to the API. Saves current layer or
        whole bitmap with a given name based on preferences. Creates the Request object with needed data filled, adds
        the image file to payload and calls api's do_request method with method defined in EXPORT_HTTP_METHOD variable.
        When the Request sent, removes temporary image file.
        When the Response object recieved, changes tha status label, prints the Response content to scrolled_window.
        :param widget: widget
        :param event: event
        :return: None
        """

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
        headers = {}
        file = open(file_name, "rb")
        payload = {"texture": ((file_name, file), "multipart/form-data")}

        request = Request(method=EXPORT_HTTP_METHOD, endpoint=endpoint, headers=headers, payload=payload)
        response = self.api.do_request(request)

        file.close()
        os.remove(file_name)

        self.textbuffer.set_text(response.payload)
        self.status_info.set_text(response.response_status.message)


# ------------ PLUGIN REGISTRATION ------------ #

class GimpExporter(gimpplugin.plugin):
    """
    Class which is liable to register the plugin in GIMP
    """

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
            "Export layer or the whole image to your API.",
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

        self.window = ExporterWindow()
        self.window.set_drawable(self.drawable)
        self.window.set_image(self.image)
        gtk.main()

        gimp.pdb.gimp_image_undo_group_end(self.image)


if __name__ == "__main__":
    exporter = GimpExporter()
    exporter.start()
