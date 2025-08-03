from langchain_community.tools.tavily_search import TavilySearchResults
from llama_parse import LlamaParse
from llama_index.core import SimpleDirectoryReader
import lancedb
import nest_asyncio
from langchain_text_splitters import RecursiveCharacterTextSplitter
from lancedb.pydantic import LanceModel, Vector
import pandas as pd
from dotenv import load_dotenv
from collections import defaultdict
from typing import List, Dict
from lancedb.embeddings import get_registry
import os
from tqdm import tqdm

load_dotenv()

embedding_model = get_registry().get("sentence-transformers").create(name = "BAAI/bge-small-en-v1.5", device = "cuda")

class BookChunk(LanceModel):
    text: str = embedding_model.SourceField()
    file_name: str
    page_number: str
    chunk_index: int
    type_doc: str
    vector: Vector(embedding_model.ndims()) = embedding_model.VectorField()


nest_asyncio.apply()

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
    


def df_to_dict_batches(df: pd.DataFrame, batch_size: int = 128):
    """
    Yields data from a DataFrame in batches of dictionaries.
    Each batch is a list of dict, suitable for LanceDB ingestion.
    """
    for start_idx in tqdm(range(0, len(df), batch_size), desc="Batches of chunks"):
        end_idx = start_idx + batch_size
        # Convert the batch of rows to a list of dict
        batch_dicts = df.iloc[start_idx:end_idx].to_dict(orient="records")
        yield batch_dicts


BOOK_TABLE_NAME = "book_chunks"


class DocumentRetriever(Retriever):

    def __init__(self, books_dir):
        print("Making the book retriever ready =====")
        db = lancedb.connect(".lancedb")

        if BOOK_TABLE_NAME not in db.table_names():
            print("Creating Database =====")
            parser = LlamaParse(result_type="text" )
            books = self._find_pdfs(books_dir)
            file_extractor = {".pdf": parser}
            data_for_parse = SimpleDirectoryReader(input_files=books, file_extractor=file_extractor)
            documents = data_for_parse.load_data(show_progress=True)

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1024,
                chunk_overlap=64,
                length_function=len,
                is_separator_regex=False,
            )

            pd_data = defaultdict(list)
            page_number = 0
            last_doc = None

            for document in documents:
                file_name = document.metadata["file_name"]
                # Infer type based on file name or path
                if "fitness" in file_name.lower():
                    doc_type = "fitness"
                elif "dietry" in file_name.lower():
                    doc_type = "dietry"
                else:
                    doc_type = "other"

                if last_doc is None or last_doc != file_name:
                    page_number = 1
                    last_doc = file_name
                else:
                    page_number += 1

                chunks = text_splitter.split_text(document.text)

                for chunk_index, chunk in enumerate(chunks):
                    pd_data["text"].append(chunk)
                    pd_data["file_name"].append(file_name)
                    pd_data["page_number"].append(page_number)
                    pd_data["chunk_index"].append(chunk_index)
                    pd_data["type_doc"].append(doc_type)
                

            df = pd.DataFrame(pd_data)
            print(f"There are {len(df)} chunks to be processed.")

            tbl = db.create_table(
                BOOK_TABLE_NAME,
                data=df_to_dict_batches(df, batch_size=10),
                schema=BookChunk,

            )
            tbl.create_fts_index('text', use_tantivy=False)
            self.tbl = tbl
        else:
            print("table is already created=====")
            self.tbl = db.open_table(BOOK_TABLE_NAME)

        print("Book Retriever is ready ====")

    def search(self, query, type_doc,limit=5) -> List[Dict]:
        return self.tbl.search(query, query_type="hybrid").limit(limit).where(f'type_doc = "{type_doc}"').to_list()


    def _find_pdfs(self, directory):
        pdf_files = []
        for root, _, files in os.walk(directory):
            for filename in files:
                if filename.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(root, filename))
        return pdf_files
