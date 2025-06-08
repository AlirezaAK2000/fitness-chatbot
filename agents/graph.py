class Graph:
    
    def __init__(self, llm, message_class):
        self.llm = llm
        self.message_class = message_class
        
    def compile(self):
        raise NotImplementedError()