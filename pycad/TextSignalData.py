import re


class TextSignalData:
    def __init__(self, i: str, t: str, k: int):
        self.text = t
        self.key = k
        try:
            cleaned_string = re.sub(r'[^0-9.]', '', i)
            self.number = int(cleaned_string)
        except ValueError as x:
            self.number = 0
