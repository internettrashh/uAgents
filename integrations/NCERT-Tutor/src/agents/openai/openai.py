# Message handler for data requests sent to this agent
import os
import requests
from uagents import Agent, Context, Model
from uagents.setup import fund_agent_if_low
from dotenv import load_dotenv
import json

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


# Configuration for making requests to OPEN AI
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {OPENAI_API_KEY}",
}

AGENT_MAILBOX_KEY = "ec9b612e-0612-4ec3-af5e-dc234f0644b6"


agent = Agent(
    name="OpenAI Agent",
    seed="your_agent_seed_hereasdasda",
    port=8007,
    endpoint=["http://127.0.0.1:8007/submit"],
    mailbox=f"{AGENT_MAILBOX_KEY}@https://agentverse.ai",
)

fund_agent_if_low(agent.wallet.address())


class Error(Model):
    text: str


class Text(Model):
    pdf: str
    success: bool
    question: str
    chapter: str
    subject: str
    standard: str
    sender: str


# class based on {"summary": "summary", "question_bank": ["question_1","question_2",...], answer_key:["answer_1","answer_2",...]}
class Summary(Model):
    summary: str
    question_bank: str
    answer_key: str
    sender: str


class Response(Model):
    text: str
    sender: str


class End(Model):
    msg: str


context = """    
    You are a helpful NCERT Tutor agent who will summarize a given chapter from NCERT and respond with a summary and a question bank with answers.
    
    Please follow these guidelines:
    1. Try to answer the question as accurately as possible, using only reliable sources like the ones provided as .
    2. Take in consideration the standard, subject, chapter, and question given.
    3. Provide a detailed summary of the chapter.
    4. Create a question bank with answers to the questions.
    5. Provide the information in the exact JSON format: {"summary": "summary", "question_bank": "question_1,question_2,...", answer_key:"answer_1,answer_2,..."}
        - summary is the summary of the chapter given
        - question bank is a newlined string of questions from the chapter
        - answer key is a newlined string of answers to the questions made from the chapter
    """

MODEL = "gpt-4-turbo"


# Send a prompt and context to the AI model and return the content of the completion
def query_openai_gpt(prompt):

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": context},
            {"role": "user", "content": prompt},
        ],
    }

    # Make the POST request to the OpenAI API
    response = requests.post(OPENAI_URL, json=data, headers=HEADERS)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        response_json = response.json()
        # Retrieve the content from the first choice in the response
        return response_json["choices"][0]["message"]["content"]
    else:
        # Handle errors (e.g., invalid API key, rate limits)
        response.raise_for_status()


# Instruct the AI model to retrieve data and context for the data and return it in machine readable JSON format
def get_data(ctx: Context, prompt: str):

    response = query_openai_gpt(prompt)

    try:
        ## try to convert response to json
        data = json.loads(response)
        ##return json data
        return data
    except Exception as ex:
        ctx.logger.exception(
            f"An error occurred retrieving data from the AI model: {ex}"
        )
        return Error(
            text="Sorry, I wasn't able to answer your request this time. Feel free to try again."
        )


def send_shared_link_data(data: Summary) -> str:
    url = "http://localhost:8080/sharedlink"
    response = requests.post(url, json=data.dict())

    if response.status_code == 200:
        return response.json()
    else:
        return None


@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info("OpenAI Agent Started")
    ctx.logger.info(f"{agent.address}")


# Message handler for data requests sent to this agent
@agent.on_message(model=Text, replies=Response)
async def handle_request(ctx: Context, sender: str, request: Text):
    ctx.logger.info(f"Got request from {sender}: {request.success}")
    request_json = json.dumps(request.dict())
    ctx.logger.info(f"Request: {request_json}")

    data = get_data(ctx, f"{request_json}")

    ctx.logger.info(f'Summary: {data["summary"]}')

    msg = Summary(
        summary=data["summary"],
        question_bank=data["question_bank"],
        answer_key=data["answer_key"],
        sender=request.sender,
    )
    url = send_shared_link_data(msg)
    if url is not None:
        hello = "The end"
        message = (
            f'{msg.summary}\n{msg.question_bank}\n<a href="{url}">Link to answers</a>'
        )
    else:
        message = f"{msg.summary}\n{msg.question_bank}\n{msg.answer_key}"

    sender = "agent1qwf80s0dqxcy6vqr2qlsyhg0jmartqvgcg70s6zr4d0rzm2te05a7fy5dy9"
    # sender="agent1qwf3e6eahspvtxxjt9adrewa8s9zc6e54srkfrd4wdavc6gy4zy9665h5m7"
    await ctx.send(sender, Response(text=message, sender=request.sender))

    return


if __name__ == "__main__":
    agent.run()
