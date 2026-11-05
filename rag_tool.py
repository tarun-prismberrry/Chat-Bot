from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from rag_pipeline import retrieve_documents



@tool
def search_uploaded_documents(query: str, config: RunnableConfig)->str:
     """
     Search the documents uploaded in the current conversation.

    Use this tool whenever the user asks questions about an uploaded
    document, its contents, author, title, chapters, concepts, or facts.

    Do not guess answers. If the retrieved document does not contain
    the requested information, explicitly say that it could not be found.
    """
     thread_id = config['configurable']['thread_id']

     documents = retrieve_documents(
          query=query,
          thread_id=thread_id,
     )
     if not documents:
        return "No relevant information found in the uploaded documents."
     result =[]
     for doc in documents:
         source = doc.metadata.get("filename", "Unknown")
         page = doc.metadata.get('page', "unknown")
         result.append(
             f"Source: {source}\n"
            f"Page: {page}\n"
            f"Content: {doc.page_content}"
         )
     return "\n\n".join(result)