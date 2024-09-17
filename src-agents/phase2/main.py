import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from enum import Enum
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import (
    VectorizedQuery
)

app = FastAPI()

load_dotenv()

class QuestionType(str, Enum):
    multiple_choice = "multiple_choice"
    true_or_false = "true_or_false"
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
        azure_ad_token_provider = token_provider,
        api_version = os.getenv("AZURE_OPENAI_VERSION"),
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
    )

deployment_name = os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME")
index_name = "movies-semantic-index"
service_endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL")

# use an embeddingsmodel to create embeddings
def get_embedding(text, model=embedding_model):
    return client.embeddings.create(input = [text], model=model).data[0].embedding

credential = None
if "AZURE_AI_SEARCH_KEY" in os.environ:
    credential = AzureKeyCredential(os.environ["AZURE_AI_SEARCH_KEY"])
else:
    credential = DefaultAzureCredential()

search_client = SearchClient(
    service_endpoint, 
    index_name, 
    credential
)

@app.get("/")
async def root():
    return {"message": "Hello Smorgs"}

@app.post("/ask", summary="Ask a question", operation_id="ask") 
async def ask_question(ask: Ask): 
    """
    Ask a question and retrieve an answer based on vector search and language model completion.
    """

    start_phrase = ask.question

    

    # Step 1: Create vectorized query based on the question
    vector = VectorizedQuery(vector=get_embedding(start_phrase), k_nearest_neighbors=5, fields="vector")

    # Step 2: Retrieve relevant documents from Azure Search (vector store)
    found_docs = list(search_client.search(
        search_text=None,
        query_type="semantic",
        semantic_configuration_name="movies-semantic-config",
        vector_queries=[vector],
        select=["title", "genre", "plot", "year"],
        top=5
    ))

    # Step 3: Convert the retrieved documents into a usable text format for context
    found_docs_as_text = " "
    for doc in found_docs:
        found_docs_as_text += f" Movie Title: {doc['title']} | Release Year: {doc['year']} | Plot: {doc['plot']}. "

    
    # Step 4: Prepare the system prompt with the retrieved context
    system_prompt = """
    You are a friendly assistant which answers questions related to Smoorghs.
    Answer the query using only the sources provided below in a friendly and concise manner.
    Answer ONLY with the facts listed in the list of context below.
    If there isn't enough information below, say you don't know.
    Do not generate answers that don't use the context below.
    """
    parameters = [system_prompt, ' Context:', found_docs_as_text , ' Question:', start_phrase]
    joined_parameters = ''.join(parameters)

    # Step 5: Generate a completion using the language model with the context provided
    response = client.chat.completions.create(
        model = deployment_name,
        messages = [{"role": "assistant", "content": joined_parameters}],
    )

    # Step 6: Prepare the answer object to be returned
    answer = Answer(
        answer=response.choices[0].message.content,
        correlationToken=ask.correlationToken,
        promptTokensUsed=response.usage.prompt_tokens,
        completionTokensUsed=response.usage.completion_tokens
    )

    return answer