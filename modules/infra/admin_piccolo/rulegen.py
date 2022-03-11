# Just a script for bootstrapping

import json

with open("../../../config/data/policy.json") as f:
    data = json.load(f)


def title(s):
    return s.replace("_", " ").replace("-", " ").title()


bot_req = ""

for key in data["rules"].keys():
    bot_req += f"### {title(key)}\n\n"
    for section in data["rules"][key].keys():
        bot_req += f'<blockquote class="quote">\n\n#### {title(section)}\n\n'
        i = 1
        for line in data["rules"][key][section]:
            bot_req += f"{i}. {line}\n"
            i += 1
        bot_req += "\n\n</blockquote>\n\n"  # Empty line

with open("api-docs/privacy.md") as policy:
    f = policy.read()

with open("api-docs/privacy.md", "w") as policy:
    policy.write(f.replace("%botreqs%", bot_req))
