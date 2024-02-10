import io

from PIL import Image


def show_image(data: bytes):
    image = Image.open(io.BytesIO(data))
    image.show()
