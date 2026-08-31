def alpha(x):
    return x


class Box:
    pass


@staticmethod
def decorated(value):
    return value


def outer():
    def nested():
        return 1
    return nested()


def alpha(z):
    return z
