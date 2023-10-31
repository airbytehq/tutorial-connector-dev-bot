# This script is running the bot with improved prompts locally in your terminal

import os
from typing import List
from langchain import PromptTemplate
import pinecone
from langchain.chains import RetrievalQA
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms import OpenAI
from langchain.vectorstores import Pinecone
from langchain.vectorstores.base import VectorStoreRetriever
from langchain.schema.document import Document

embeddings = OpenAIEmbeddings()
pinecone.init(api_key=os.environ["PINECONE_KEY"], environment=os.environ["PINECONE_ENV"])
index = pinecone.Index(os.environ["PINECONE_INDEX"])
vector_store = Pinecone(index, embeddings.embed_query, "text")

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


qa = RetrievalQA.from_chain_type(llm=OpenAI(temperature=0), chain_type="stuff", retriever=ContextualRetriever(vectorstore=vector_store), chain_type_kwargs={"prompt": prompt})

print("Connector development help bot. What do you want to know?")
while True:
    query = input("")
    answer = qa.run(query)
    print(answer)
    print("\nWhat else can I help you with:")
