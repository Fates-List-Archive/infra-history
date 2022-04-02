from pydantic import BaseModel 

class StaffApp(BaseModel):
    id: str 
    title: str
    question: str 
    description: str
    min_length: int 
    max_length: int
    paragraph: bool
    type: str = "text"


class StaffAppPane(BaseModel):
    title: str 
    description: str 
    questions: list[StaffApp]

questions = [
    StaffAppPane(
        title="Basics",
        description="Firstly, the basics",
        questions=[
            StaffApp(
                id="tz",
                title="Time Zone",
                question="Please enter your timezone (the 3 letter code)",
                description="IST, PST, EST etc. Don't use relative-to-UTC based here!",
                min_length=3,
                max_length=3,
                paragraph=False
            ),
            StaffApp(
                id="age",
                title="Age",
                question="Please enter your age (14+ only!)",
                description="What is your age? Will be investigated so don't lie!",
                min_length=2,
                max_length=2,
                paragraph=False,
                type = "number"
            ),
            StaffApp(
                id="lang",
                title="Languages",
                question="What languages do you know?",
                description="I am good at English, decent at Spanish........",
                min_length=5,
                max_length=100,
                paragraph=False
            ),
            StaffApp(
                id="history",
                title="History",
                question="Have you ever been demoted from a bot list before? If so, why?",
                description="Yes, I have been demoted from Rovel Discord List because I was promoting misinformation...",
                min_length=5,
                max_length=200,
                paragraph=True
            ),
            StaffApp(
                id="motivation",
                title="Motivation",
                question="Why do you want to be a bot reviewer and how much experience do you have?",
                description="I have been a bot reviewer for 3-4 years on Rovel Discord List, I have a lot of experience in bot development and I am very motivated to work on this project and to help out the community at large.",
                min_length=50,
                max_length=65536,
                paragraph=True
            ),
        ]
    ),
    StaffAppPane(
        title="Personality",
        description="This section is just to see how well you can communicate with other people and argue with completely random points. You will need to use Google here. If you dont understand something, look up each name on the internet",
        questions=[
            StaffApp(
                id="sumcat",
                title="Summary",
                question="Summarize the life on one cat from: Mistystar, Graystripe, Frostpaw, Flamepaw/Nightleap or Sunbeam?",
                description="Use Google here to find information. Example: Mistystar is a blue grey-she cat currently living in RiverClan...",
                min_length=65535,
                max_length=65536,
                paragraph=True
            ),
            StaffApp(
                id="catname",
                title="Random Cat",
                question="Which cat (or group of cats) in Warrior Cats best describes you as a person (on Discord) and why? Use evidence and reasoning from the books to support you're thesis and PETAL IGCSE format. Use at least 5 paragraphs",
                description="Use Google here to find information. Be careful about punctuation. Example: Brokenstar and Leopardstar best describe me.",
                min_length=65535,
                max_length=65536,
                paragraph=True
            ),
            StaffApp(
                id="webserver",
                title="Web Server",
                question="What, in your opinion is the most superior web server",
                description="Use Google here to find information. Example: Nginx is the most superior web server due to it's speed and having a technologically superior architecture.",
                min_length=20,
                max_length=65536,
                paragraph=True
            ),
            StaffApp(
                id="os",
                title="Operating System",
                question="Which operating system do you use and why? Do you use a custom client on Discord?",
                description="Example: I use Linux because my PC is extremely old, I use BetterCord on Discord because of custom plugins.",
                min_length=20,
                max_length=65536,
                paragraph=True
            ),
        ]
    ),
    StaffAppPane(
        title="Agreements",
        description="This section is to ensure you understand some basic guidelines",
        questions=[
            StaffApp(
                id="agreement",
                title="Agreement",
                question="Do you understand that being staff here is a privilege and that you may demoted without warning?",
                description="Be sure to reread your previous answers before accepting!",
                min_length=10,
                max_length=2048,
                paragraph=True
            )
        ]
    )
]