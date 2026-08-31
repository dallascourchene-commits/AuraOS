def deco(fn):
    return fn

@deco
def outer(flag):
    def inner():
        return flag

    if flag:
        def conditional():
            return flag

    def inner():
        return 2

    class Local:
        def method(self):
            def deeply():
                return flag
            return deeply

    return inner

class Box:
    def method(self):
        def helper():
            return 1
        return helper

    class Nested:
        def n(self):
            return 3

def tail():
    return 0
