from db.retrievers import WebRetriever,  DocumentRetriever


def get_search_web_tool(num_results = 5):
    web_retriever = WebRetriever(limit = num_results)
    def search_web(query: str):
        """Search the web for the query and returns the top 5 most related results.
        Args:
            query: The query to search for.
        """

        results = web_retriever.search(query)
        return results
    
    return search_web



def get_search_books_tool(document_retriever: DocumentRetriever, type_doc: str, num_results = 5):

    def search_books(query: str):
        """Searches the documents inside the database and returns the top most related resutls.
        Args:
            query: The query to search for.
        """
        
        results = document_retriever.search(query, type_doc, num_results)
        # results = [
        #     {
        #         "content": result['text'],
        #         "score": result['_relevance_score']
        #     } for result in results
        # ]
        return results
    
    return search_books