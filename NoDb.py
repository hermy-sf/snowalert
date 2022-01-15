import json

class NoDb:
    def __init__(self, name, init=None):
        self.name = name
        try:
            self.open()
        except FileNotFoundError as e:
            self.d = {} if init is None else init
            self.flush()

    def flush(self):
        with open(self.name, 'w') as f:
            json.dump(self.d, f)

    def open(self):
        with open(self.name, 'r') as f:
            d = json.load(f)
        self.d = d

#db = NoDb("contents.json", init={'alerts': {}})
