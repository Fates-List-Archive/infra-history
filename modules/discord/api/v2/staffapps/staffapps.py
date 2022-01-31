from modules.core import *

import pytz

from ..base import API_VERSION

from .models import StaffAppCreate, StaffAppQuestions, StaffAppQuestion, APIResponse

router = APIRouter(
    prefix=f"/api/v{API_VERSION}/staff-apps",
    include_in_schema=True,
    tags=[f"API v{API_VERSION} - Staff Apps"],
)

app_version = "1"

staff_app_questions = StaffAppQuestions(
    questions=[
        StaffAppQuestion(
            id="tz",
            title="Time Zone",
            question="Please enter your timezone (the 3 letter code).",
            minlength=3,
            maxlength=3
        ),
        StaffAppQuestion(
            id="age",
            title="Age",
            question="What is your age? Just the number Do not lie, we will investigate and find out!",
            minlength=2,
            maxlength=3,
        ),
        StaffAppQuestion(
            id="exp",
            title="Your Experience",
            question="Do you have experience being a bot reviewer? If so, from where and how long/much experience do you have? How confident are you at handling bots?",
        ),
        StaffAppQuestion(
            id="lang",
            title="Languages/Communication",
            question="How well do you know English? What other languages do you know? How good are you at speaking/talking/listening?",
        ),
        StaffAppQuestion(
            id="why",
            title="Why should we accept you?",
            question="Why are you interested in being staff here at Fates List?",
        ),
        StaffAppQuestion(
            id="contrib",
            title="Contributions",
            question="What do you think you can contribute to Fates List?",
        ),
        StaffAppQuestion(
            id="talent",
            title="Talent",
            question="What, in your opinion, are your strengths and weaknesses?",
        ),
        StaffAppQuestion(
            id="will",
            title="Will you be available to work?",
            question="How willing are you to learn new tools and processes?",
        ),
        StaffAppQuestion(
            id="agree",
            title="Agreements",
            question="Do you understand that being staff here is a privilege and that you may demoted without warning based on your performance.",
            minlength=10,
            maxlength=50
        ),
    ]
)

@router.get("/questions", response_model=StaffAppQuestions)
async def get_staff_app_questions(request: Request):
    return staff_app_questions

@router.post(
    "/{user_id}", 
    response_model=APIResponse,
    dependencies=[
        Depends(user_auth_check)
    ],
)
async def post_staff_app(request: Request, app: StaffAppCreate, user_id: int):
    user = await get_user(user_id)
    if not user:
        return abort(404)

    check = await redis_db.get(f"staffapp:{user_id}")
    if check and check.decode() == app_version:
        return api_error("You have already submitted a staff application recently!")

    staff_app = f"User ID: {user_id}\nUsername: {user['username']}#{user['disc']}\n\n"
    for question in staff_app_questions.questions:
        if question.id not in app.answers:
            return api_error(f"Missing answer for question {question.id}")
        elif len(app.answers[question.id]) < question.minlength:
            return api_error(f"Answer for question {question.id} is too short")
        elif len(app.answers[question.id]) > question.maxlength:
            return api_error(f"Answer for question {question.id} is too long")
        elif question.id == "tz":
            if not app.answers[question.id].isalpha(): 
                return api_error(f"Answer for question {question.id} is not a valid timezone")
            app.answers[question.id] = app.answers[question.id].upper()

        staff_app += f"{question.title} ({question.id}) [{question.question}]: {app.answers[question.id]}\n\n"

    await redis_ipc_new(
        request.app.state.worker_session.redis, 
        "SENDMSG", 
        msg = {
            "content": f"**New Staff Application** <@&{staff_ping_add_role}>", 
            "file_name": f"staffapp-{user_id}.txt", 
            "file_content": staff_app, 
            "channel_id": str(staff_apps_channel),
            "mention_roles": [str(staff_ping_add_role)]
        }
    )

    await redis_db.set(f"staffapp:{user_id}", app_version, ex=60*60*24)
    return api_success()
