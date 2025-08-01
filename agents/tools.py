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



def get_search_books_tool(book_retriever: DocumentRetriever):

    def search_books(query: str):
        """Searches the books inside the database and returns the top 5 most related resutls.
        Args:
            query: The query to search for.
        """
        
        results = book_retriever.search(query)
        results = [result['text'] for result in results]
        print(f"****************\nretrieved text : \n results \n*********************")
        return results
    
    return search_books