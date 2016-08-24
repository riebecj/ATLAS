from mbtiles import MbtileSet
import tornado.ioloop
import tornado.web
import threading
import os
import time


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('''
        <h1> Server is running... </h1>
		''')

	
class MbtilesHandler(tornado.web.RequestHandler):
    def initialize(self, ext, mbtiles):
        self.ext = ext
        self.mbtiles = mbtiles
        self.tileset = MbtileSet(mbtiles=mbtiles)

    def get(self, z, x, y):
        origin = self.get_arguments('origin')
        # invert y axis to top origin
        ymax = 1 << int(z);
        y = ymax - int(y) - 1;

        tile = self.tileset.get_tile(z, x, y) 
        if self.ext == 'png':
            self.set_header('Content-Type', 'image/png')
            self.write(tile.get_png())
        elif self.ext == 'json':
            callback = self.get_arguments('callback')
            try:
                callback = callback[0]
            except IndexError:
                callback = None

            self.set_header('Content-Type', 'application/json')
            if callback:
                self.write("%s(%s)" % (callback, tile.get_json()))
            else:
                self.write(tile.get_json())