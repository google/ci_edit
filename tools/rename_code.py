#!/bin/env python3

import os
import re
import sys

if len(sys.argv) < 2 :#or sys.argv[1] == "--help":
    print("rename_code.py <source_code_directory>")
    print("Update python code to new style.")
    sys.exit(0)

old_names = set()
class_names = set()
for (dir, dirs, files) in os.walk(sys.argv[1]):
    if dir == ".git":
        continue
    for file in files:
        if not file.endswith(".py"):
            continue
        path = os.path.join(dir, file)
        print("-----", path)
        with open(path) as f:
            data = f.read()
        for i in re.finditer(r"\bdef\s+(\w+)", data):
            name = i.group(1)
            if re.search(r"[A-Z]", name):
                print(":", name)
                old_names.add(name)
        for i in re.finditer(r"\bclass\s+(\w+)", data):
            name = i.group(1)
            class_names.add(name)
#print("old_names:", old_names)
#print("class_names:", class_names)
for i in class_names:
    if i in old_names:
        print(i, "is also a class name")
        old_names.remove(i)
#print("old_names:", old_names)
find_old_name = re.compile(r"(\b"+r"\b|\b".join(old_names)+r")\b")
for (dir, dirs, files) in os.walk(sys.argv[1]):
    if dir == ".git":
        continue
    for file in files:
        if not file.endswith(".py"):
            continue
        path = os.path.join(dir, file)
        print("-----", path)
        with open(path, "r+") as f:
            data = find_old_name.sub(
                    lambda x: re.sub(
                        "([A-Z])",
                        lambda n: "_"+n.group(1).lower(),
                        x.group(1)),
                    f.read())
            f.seek(0)
            f.write(data)


