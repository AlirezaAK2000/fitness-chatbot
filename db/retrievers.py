from langchain_community.tools.tavily_search import TavilySearchResults


class Retriever:

    def search(self, query: str, limit: int):
        raise NotImplementedError()

        
class WebRetriever(Retriever):

    def __init__(self, limit = 5):

        self.tool = TavilySearchResults(
            max_results=limit,
            search_depth="advanced",
        )

    def search(self, query):
        return self.tool.invoke(query)