with open("/home/meow/api-v3/src/models.rs") as src_file:
    src = src_file.read()

for line in src.split("\n"):
    print(line)