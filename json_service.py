from json import dump

import data


def make_a_database():
    with open("teachers.json", "w") as f_out:
        dump(data.teachers, f_out)
