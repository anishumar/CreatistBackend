from enum import Enum

class MediaType(Enum):
    IMAGE = "image"
    VIDEO = "video"


class UserGenre(Enum):
    VIDEOGRAPHER = "videographer"
    PHOTOGRAPHER = "photographer"
    VOCALIST = "vocalist"
    DANCER = "dancer"
    DRUMMER = "drummer"
    EDITOR = "editor"
    ACTOR = "actor"
    COMPOSER = "composer"
    DIRECTOR = "director"
    WRITER = "writer"
    GRAPHICDESIGNER = "graphicDesigner"
    SINGER = "singer"
    GUITARIST = "guitarist"
    SITARIST = "sitarist"
    PIANIST = "pianist"
    VIOLINIST = "violinist"
    FLUTIST = "flutist"
    PERCUSSIONIST = "percussionist"


class PaymentMode(Enum):
    FREE = "free"
    PAID = "paid"


class WorkMode(Enum):
    ONLINE = "Online"
    ONSITE = "Onsite"
    ONLINE_ONSITE = "OnsiteOnline"

