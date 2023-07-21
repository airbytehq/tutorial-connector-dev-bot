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
from langchain.schema.document import Document

embeddings = OpenAIEmbeddings()
pinecone.init(api_key=os.environ["PINECONE_KEY"], environment=os.environ["PINECONE_ENV"])
index = pinecone.Index(os.environ["PINECONE_INDEX"])
vector_store = Pinecone(index, embeddings.embed_query, "text")


prompt_template = """You are a question-answering bot operating on Github issues and documentation pages for a product called connector builder. The documentation pages document what can be done, the issues document future plans and bugs. Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. Always state were you got this information from (and the github issue number if applicable).
If the answer is based on a Github issue that's not closed yet, add 'This issue is not closed yet - the feature might not be shipped yet' to the answer.

{context}

Question: {question}
Helpful Answer:"""
prompt = PromptTemplate(
    template=prompt_template, input_variables=["context", "question"]
)
class ConnectorDevelopmentPrompt(PromptTemplate):
    def format_document(doc: Document, prompt: PromptTemplate) -> str:
        if doc.metadata["_airbyte_stream"] == "DatasetItems":
            return f"Excerpt from documentation page: {doc.page_content}"
        elif doc.metadata["_airbyte_stream"] == "issues":
            return f"Excerpt from Github issue: {doc.page_content}, issue number: {doc.metadata['number']}, issue state: {doc.metadata['state']}"
        elif doc.metadata["_airbyte_stream"] == "threads" or doc.metadata["_airbyte_stream"] == "channel_messages":
            return f"Excerpt from Slack thread: {doc.page_content}"
        else:
            return super().format_document(doc, prompt)


document_prompt = ConnectorDevelopmentPrompt(input_variables=["page_content"], template="{page_content}")
qa = RetrievalQA.from_chain_type(llm=OpenAI(temperature=0), chain_type="stuff", retriever=vector_store.as_retriever(), chain_type_kwargs={"prompt": prompt, "document_prompt": document_prompt})

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