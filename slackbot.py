# This script is running the bot on Slack

import os
from langchain.prompts import PromptTemplate
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
import pinecone
from langchain.chains import RetrievalQA
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms import OpenAI
from langchain.vectorstores import Pinecone
from langchain.vectorstores.base import VectorStoreRetriever
from typing import List
from langchain.schema.document import Document

# Initialize Pinecone
embeddings = OpenAIEmbeddings()
pinecone.init(api_key=os.environ["PINECONE_KEY"], environment=os.environ["PINECONE_ENV"])
index = pinecone.Index(os.environ["PINECONE_INDEX"])
vector_store = Pinecone(index, embeddings.embed_query, "text")


# Define prompts
prompt_template = """You are a question-answering bot operating on Github issues and documentation pages for a product called connector builder. The documentation pages document what can be done, the issues document future plans and bugs. Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. State were you got this information from (and the github issue number if applicable), but do only if you used the information in your answer.

{context}

Question: {question}
Helpful Answer:"""
prompt = PromptTemplate(
    template=prompt_template, input_variables=["context", "question"]
)
class ContextualRetriever(VectorStoreRetriever):
    def _get_relevant_documents(self, query: str, *, run_manager) -> List[Document]:
        docs = super()._get_relevant_documents(query, run_manager=run_manager)
        return [self.format_doc(doc) for doc in docs]

    def format_doc(self, doc: Document) -> Document:
        if doc.metadata["_airbyte_stream"] == "item_collection":
            doc.page_content = f"Excerpt from documentation page: {doc.page_content}"
        elif doc.metadata["_airbyte_stream"] == "issues":
            doc.page_content =  f"Excerpt from Github issue: {doc.page_content}, issue number: {int(doc.metadata['number']):d}, issue state: {doc.metadata['state']}"
        elif doc.metadata["_airbyte_stream"] == "threads" or doc.metadata["_airbyte_stream"] == "channel_messages":
            doc.page_content =  f"Excerpt from Slack thread: {doc.page_content}"
        return doc


# Initialize the QA system
qa = RetrievalQA.from_chain_type(llm=OpenAI(temperature=0), chain_type="stuff", retriever=ContextualRetriever(vectorstore=vector_store), chain_type_kwargs={"prompt": prompt})


# Wire it up to Slack
slack_web_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

handled_messages = {}

def process(_: SocketModeClient, socket_mode_request: SocketModeRequest):
    if socket_mode_request.type == "events_api":
        event = socket_mode_request.payload.get("event", {})
        client_msg_id = event.get("client_msg_id")
        if event.get("type") == "app_mention" and not handled_messages.get(client_msg_id):
            handled_messages[client_msg_id] = True
            channel_id = event.get("channel")
            text = event.get("text")
            result = qa.run(text)
            slack_web_client.chat_postMessage(channel=channel_id, text=result)
    
    return SocketModeResponse(envelope_id=socket_mode_request.envelope_id)

socket_mode_client = SocketModeClient(
    app_token=os.environ["SLACK_APP_TOKEN"], 
    web_client=slack_web_client
)
socket_mode_client.socket_mode_request_listeners.append(process)

socket_mode_client.connect()
print("listening")
from threading import Event
Event().wait()
