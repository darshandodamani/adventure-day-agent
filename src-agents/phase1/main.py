import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from enum import Enum
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import re
from word2number import w2n

app = FastAPI()

load_dotenv()

class QuestionType(str, Enum):
    multiple_choice = "multiple_choice"
    true_false = "true_or_false"
    popular_choice = "popular_choice"
    estimation = "estimation"

class Ask(BaseModel):
    question: str | None = None
    type: QuestionType
    correlationToken: str | None = None

class Answer(BaseModel):
    answer: str
    correlationToken: str | None = None
    promptTokensUsed: int | None = None
    completionTokensUsed: int | None = None

client: AzureOpenAI

if "AZURE_OPENAI_API_KEY" in os.environ:
    client = AzureOpenAI(
        api_key = os.getenv("AZURE_OPENAI_API_KEY"),  
        api_version = os.getenv("AZURE_OPENAI_VERSION"),
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    )
else:
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = AzureOpenAI(
        azure_ad_token_provider=token_provider,
        api_version = os.getenv("AZURE_OPENAI_VERSION"),
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
    )

deployment_name = os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME")

@app.get("/")
async def root():
    return {"message": "Hello Smoorghs"}





def extract_number(sentence: str) -> str:

    # Extract the word representing the number
    number_word = re.search(r'\b(one|two|three|four|five|six|seven|eight|nine|ten)\b', sentence, re.IGNORECASE)

    if number_word:
        # Convert the word to an integer
        number_int = w2n.word_to_num(number_word.group())
        return str(number_int)
    else:
        print("No number word found in the sentence.")
    

@app.post("/ask", summary="Ask a question", operation_id="ask") 
async def ask_question(ask: Ask):
    # """
    # # Ask a question
    # """

    # Send a completion call to generate an answer
    print('Sending a request to openai')
    
    start_phrase =  ask.question
    response: openai.types.chat.chat_completion.ChatCompletion = None
    
    response = client.chat.completions.create(
        model = deployment_name,
        messages = [{"role" : "assistant", "content" : start_phrase}, 
                     { "role" : "system", "content" : "Answer this question:"}]
    )

    print(response.choices[0].message.content)
    print(response)
    answer_string = response.choices[0].message.content
    if ask.type == QuestionType.multiple_choice:
        answer_string = answer_string[3:]
    elif ask.type == QuestionType.true_or_false:
        answer_string = answer_string.lower()
    elif ask.type == QuestionType.estimation:
        answer_string = extract_number(answer_string)
    answer = Answer(answer=answer_string)
    answer.correlationToken = ask.correlationToken
    answer.promptTokensUsed = response.usage.prompt_tokens
    answer.completionTokensUsed = response.usage.completion_tokens

    return answer