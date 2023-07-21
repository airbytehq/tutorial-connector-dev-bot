# This script is running the bot with improved prompts locally in your terminal

import os
from langchain import PromptTemplate
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

print("Connector development help bot. What do you want to know?")
while True:
    query = input("")
    answer = qa.run(query)
    print(answer)
    print("\nWhat else can I help you with:")