Fates List uses [messagepack](https://msgpack.org/index.html) as a initial transport system because lots of the data we send are not supported/are undefined behaviour on JSON and because many languages have support for it. Our tooling was also designed with messagepack in mind.

We provide a python script to allow users to parse this messagepack data into a usable form such as a python dictionary or a JSON file (albiet with corruption and compatibility issues on some JSON implementations, particularly JavaScript which was the reason why messagepack was chosen in the first place). 

The below script requires the ``msgpack`` library which can be installed via ``pip install msgpack``. Feel free to ask for help with this on our support server if needed:

```py
import msgpack

user_id = input("User ID: ")

with open(f"data-request-{user_id}.fates", "rb") as f:
    data = f.read()

fates_data = msgpack.unpackb(data)

# Do something with fates_data (python dictionary). 
# Example, to turn the data into a (broken on JS but spec-compliant) JSON file:
import json

with open("output-file.json", "w") as f:
    f.write(json.dumps(fates_data))
```