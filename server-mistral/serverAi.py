from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.embeddings import resolve_embed_model
from llama_index.llms.ollama import Ollama
from llama_index.core import SimpleDirectoryReader, StorageContext
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.postgres import PGVectorStore
import textwrap
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        data = json.loads(body)

        print(f"Received POST request with data: {data}")

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Data received successfully!')
        documents = SimpleDirectoryReader("./story").load_data()
        print("Document ID:", documents[0].doc_id)

        # bge embedding model
        Settings.embed_model = resolve_embed_model("local:BAAI/bge-small-en-v1.5")

        # ollama
        Settings.llm = Ollama(model="mistral",request_timeout=300000.0)

        import psycopg2

        connection_string = "postgresql://postgres:aziz@172.31.160.1:5432"
        db_name = "vectorstory_db"
        conn = psycopg2.connect(connection_string)
        conn.autocommit = True

        #with conn.cursor() as c:
        #  c.execute(f"DROP DATABASE IF EXISTS {db_name}")
        # c.execute(f"CREATE DATABASE {db_name}")
            

        from sqlalchemy import make_url

        url = make_url(connection_string)



        vector_store = PGVectorStore.from_params(
            database="vectorstory_db",
            host=url.host,
            password=url.password,
            port=url.port,
            user=url.username,
            table_name="story_data",
            embed_dim=384, 
        )


        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_documents(
            documents, storage_context=storage_context, show_progress=True
        )
        query_engine = index.as_query_engine()
        query_string = json.dumps(data)
        response = query_engine.query(query_string
                                      
                                      )
        print(textwrap.fill(str(response), 100))



if __name__ == '__main__':
    server_address = ('', 5003)
    httpd = HTTPServer(server_address, RequestHandler)
    print('Starting server on http://localhost:5003')
    httpd.serve_forever()
