import uuid


def get_file_path(filename):
    ext = filename.split(".")[-1]
    randomized_filename = "%s.%s" % (uuid.uuid4(), ext)
    return randomized_filename
