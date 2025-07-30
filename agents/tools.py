from db.retrievers import WebRetriever


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