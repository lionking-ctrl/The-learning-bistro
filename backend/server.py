import os
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from pypdf import PdfReader

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama, OllamaEmbeddings
from fastapi.middleware.cors import CORSMiddleware

# ============================================================
# ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

logger = logging.getLogger("restaurant-ai")


# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://127.0.0.1:11434",
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen3:30b",
)

OLLAMA_EMBED_MODEL = os.getenv(
    "OLLAMA_EMBED_MODEL",
    "nomic-embed-text",
)

CASSANDRA_HOST = os.getenv(
    "CASSANDRA_HOST",
    "127.0.0.1",
)

CASSANDRA_PORT = int(
    os.getenv(
        "CASSANDRA_PORT",
        "9042",
    )
)

CASSANDRA_KEYSPACE = os.getenv(
    "CASSANDRA_KEYSPACE",
    "restaurant_ai",
)

CASSANDRA_USERNAME = os.getenv(
    "CASSANDRA_USERNAME",
    "",
)

CASSANDRA_PASSWORD = os.getenv(
    "CASSANDRA_PASSWORD",
    "",
)

PDF_DIRECTORY = BASE_DIR / "documents"

PDF_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Restaurant AI Agent",
    description="Restaurant management AI backend using FastAPI, LangChain, Ollama and Cassandra",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# CASSANDRA
# ============================================================

cluster = None
session = None


def connect_cassandra():

    global cluster
    global session

    logger.info(
        "CASSANDRA CONNECT | host=%s | port=%s",
        CASSANDRA_HOST,
        CASSANDRA_PORT,
    )

    try:

        if CASSANDRA_USERNAME and CASSANDRA_PASSWORD:

            auth_provider = PlainTextAuthProvider(
                username=CASSANDRA_USERNAME,
                password=CASSANDRA_PASSWORD,
            )

            cluster = Cluster(
                [CASSANDRA_HOST],
                port=CASSANDRA_PORT,
                auth_provider=auth_provider,
            )

        else:

            cluster = Cluster(
                [CASSANDRA_HOST],
                port=CASSANDRA_PORT,
            )

        session = cluster.connect()

        logger.info(
            "CASSANDRA CONNECTED"
        )

        create_database()

    except Exception:

        logger.exception(
            "CASSANDRA CONNECTION FAILED"
        )

        raise


def create_database():

    logger.info(
        "CASSANDRA INIT | keyspace=%s",
        CASSANDRA_KEYSPACE,
    )

    session.execute(
        f"""
        CREATE KEYSPACE IF NOT EXISTS {CASSANDRA_KEYSPACE}
        WITH replication = {{
            'class': 'SimpleStrategy',
            'replication_factor': 1
        }}
        """
    )

    session.set_keyspace(
        CASSANDRA_KEYSPACE
    )

    # --------------------------------------------------------
    # RESTAURANT TABLE
    # --------------------------------------------------------

    session.execute(
        """
        CREATE TABLE IF NOT EXISTS restaurant_info (
            id text PRIMARY KEY,
            name text,
            address text,
            phone text,
            opening_time text,
            closing_time text
        )
        """
    )

    # --------------------------------------------------------
    # CUSTOMERS
    # --------------------------------------------------------

    session.execute(
        """
        CREATE TABLE IF NOT EXISTS customers (
            customer_id uuid PRIMARY KEY,
            name text,
            phone text,
            email text
        )
        """
    )

    # --------------------------------------------------------
    # RESERVATIONS
    # --------------------------------------------------------

    session.execute(
        """
        CREATE TABLE IF NOT EXISTS reservations (
            reservation_id uuid PRIMARY KEY,
            customer_name text,
            phone text,
            reservation_date date,
            reservation_time text,
            guests int,
            status text
        )
        """
    )

    # --------------------------------------------------------
    # DOCUMENT CHUNKS
    #
    # The first implementation stores embeddings as a list.
    # This keeps the example simple and works independently
    # of Cassandra vector-search configuration.
    # --------------------------------------------------------

    session.execute(
        """
        CREATE TABLE IF NOT EXISTS document_chunks (
            chunk_id uuid PRIMARY KEY,
            document_name text,
            page_number int,
            content text,
            embedding list<float>
        )
        """
    )

    logger.info(
        "CASSANDRA SCHEMA READY"
    )


# ============================================================
# LANGCHAIN / OLLAMA
# ============================================================

logger.info(
    "OLLAMA CONFIG | host=%s | model=%s | embedding_model=%s",
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_EMBED_MODEL,
)


llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_HOST,
    temperature=0,
)


embeddings = OllamaEmbeddings(
    model=OLLAMA_EMBED_MODEL,
    base_url=OLLAMA_HOST,
)


# ============================================================
# TEXT SPLITTER
# ============================================================

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
)


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup():

    logger.info(
        "APPLICATION STARTING"
    )

    connect_cassandra()

    logger.info(
        "APPLICATION READY"
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
@app.get("/api/health")
def health():

    return {
        "status": "UP",
        "ollama": OLLAMA_HOST,
        "model": OLLAMA_MODEL,
        "cassandra": CASSANDRA_HOST,
        "keyspace": CASSANDRA_KEYSPACE,
    }


# ============================================================
# PDF EXTRACTION
# ============================================================

def extract_pdf(
    file_path: Path,
):

    logger.info(
        "PDF EXTRACTION START | file=%s",
        file_path.name,
    )

    reader = PdfReader(
        str(file_path)
    )

    documents = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):

        text = page.extract_text()

        if not text:
            continue

        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source": file_path.name,
                    "page": page_number,
                },
            )
        )

    logger.info(
        "PDF EXTRACTION COMPLETE | file=%s | pages=%s",
        file_path.name,
        len(documents),
    )

    return documents


# ============================================================
# PDF → CHUNKS → EMBEDDINGS → CASSANDRA
# ============================================================

def index_pdf(
    file_path: Path,
):

    logger.info(
        "RAG INDEX START | file=%s",
        file_path.name,
    )

    documents = extract_pdf(
        file_path
    )

    if not documents:

        raise ValueError(
            "No readable text found in PDF."
        )

    chunks = text_splitter.split_documents(
        documents
    )

    logger.info(
        "RAG CHUNKING COMPLETE | chunks=%s",
        len(chunks),
    )

    for index, chunk in enumerate(
        chunks
    ):

        logger.info(
            "EMBEDDING | chunk=%s/%s | page=%s",
            index + 1,
            len(chunks),
            chunk.metadata.get("page"),
        )

        vector = embeddings.embed_query(
            chunk.page_content
        )

        session.execute(
            """
            INSERT INTO document_chunks (
                chunk_id,
                document_name,
                page_number,
                content,
                embedding
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                uuid.uuid4(),
                file_path.name,
                chunk.metadata.get("page"),
                chunk.page_content,
                vector,
            ),
        )

    logger.info(
        "RAG INDEX COMPLETE | file=%s | chunks=%s",
        file_path.name,
        len(chunks),
    )

    return len(chunks)


# ============================================================
# PDF UPLOAD
# ============================================================

@app.post("/api/documents/upload")
async def upload_pdf(
    file: UploadFile = File(...),
):

    if not file.filename.lower().endswith(
        ".pdf"
    ):

        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    destination = (
        PDF_DIRECTORY /
        file.filename
    )

    logger.info(
        "PDF UPLOAD | filename=%s",
        file.filename,
    )

    contents = await file.read()

    destination.write_bytes(
        contents
    )

    try:

        chunk_count = index_pdf(
            destination
        )

    except Exception as exc:

        logger.exception(
            "PDF INDEXING FAILED"
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    return {
        "status": "success",
        "filename": file.filename,
        "chunks": chunk_count,
    }


# ============================================================
# RAG RETRIEVAL
# ============================================================

def retrieve_documents(
    query: str,
    top_k: int = 5,
):

    logger.info(
        "RAG RETRIEVAL START | query=%s",
        query,
    )

    query_vector = embeddings.embed_query(
        query
    )

    rows = session.execute(
        """
        SELECT
            chunk_id,
            document_name,
            page_number,
            content,
            embedding
        FROM document_chunks
        """
    )

    results = []

    # --------------------------------------------------------
    # Simple cosine similarity
    #
    # This is intentionally simple for the first version.
    # Later we can replace this with Cassandra native vector
    # search.
    # --------------------------------------------------------

    import math

    def cosine_similarity(a, b):

        if not a or not b:
            return 0.0

        dot = sum(
            x * y
            for x, y in zip(a, b)
        )

        norm_a = math.sqrt(
            sum(x * x for x in a)
        )

        norm_b = math.sqrt(
            sum(y * y for y in b)
        )

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (
            norm_a * norm_b
        )

    for row in rows:

        score = cosine_similarity(
            query_vector,
            row.embedding,
        )

        results.append(
            (
                score,
                row,
            )
        )

    results.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    selected = results[:top_k]

    logger.info(
        "RAG RETRIEVAL COMPLETE | results=%s",
        len(selected),
    )

    for rank, (
        score,
        row,
    ) in enumerate(
        selected,
        start=1,
    ):

        logger.info(
            "RAG RESULT | rank=%s | score=%.4f | document=%s | page=%s",
            rank,
            score,
            row.document_name,
            row.page_number,
        )

    return selected


# ============================================================
# ASK REQUEST
# ============================================================

class AskRequest(BaseModel):

    question: str

    top_k: int = 5


# ============================================================
# RAG + OLLAMA
# ============================================================

@app.post("/api/ask")
def ask(
    request: AskRequest,
):

    logger.info(
        "AGENT REQUEST | question=%s",
        request.question,
    )

    # --------------------------------------------------------
    # STEP 1
    # Retrieve relevant PDF information
    # --------------------------------------------------------

    retrieved = retrieve_documents(
        request.question,
        request.top_k,
    )

    if not retrieved:

        context = (
            "No relevant restaurant information "
            "was found in the uploaded documents."
        )

    else:

        context_parts = []

        for score, row in retrieved:

            context_parts.append(
                f"""
Document: {row.document_name}
Page: {row.page_number}
Relevance: {score:.4f}

{row.content}
"""
            )

        context = "\n\n".join(
            context_parts
        )

    # --------------------------------------------------------
    # STEP 2
    # Give retrieved context to Ollama
    # --------------------------------------------------------

    prompt = f"""
You are an AI assistant for a restaurant.

Answer the customer's question using ONLY
the restaurant information provided below.

If the information is not present,
say that the information is not available
in the restaurant documents.

Do not invent menu items, prices,
timings, availability or policies.

RESTAURANT INFORMATION
======================

{context}

CUSTOMER QUESTION
=================

{request.question}
"""

    logger.info(
        "OLLAMA REQUEST | model=%s | context_chunks=%s",
        OLLAMA_MODEL,
        len(retrieved),
    )

    response = llm.invoke(
        prompt
    )

    answer = response.content

    logger.info(
        "OLLAMA RESPONSE | answer_length=%s",
        len(answer),
    )

    return {
        "question": request.question,
        "answer": answer,
        "sources": [
            {
                "document": row.document_name,
                "page": row.page_number,
                "score": round(
                    score,
                    4,
                ),
            }
            for score, row in retrieved
        ],
    }


# ============================================================
# RESERVATION REQUEST
# ============================================================

class ReservationRequest(BaseModel):

    customer_name: str

    phone: str = ""

    reservation_date: str

    reservation_time: str

    guests: int


# ============================================================
# CREATE RESERVATION
# ============================================================

@app.post("/api/reservations")
def create_reservation(
    request: ReservationRequest,
):

    logger.info(
        "RESERVATION REQUEST | customer=%s | date=%s | time=%s | guests=%s",
        request.customer_name,
        request.reservation_date,
        request.reservation_time,
        request.guests,
    )

    if request.guests < 1:
        raise HTTPException(
            status_code=400,
            detail="Guests must be at least 1.",
        )

    try:
        reservation_date = datetime.strptime(
            request.reservation_date,
            "%Y-%m-%d",
        ).date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="reservation_date must use YYYY-MM-DD format.",
        )

    try:
        datetime.strptime(
            request.reservation_time,
            "%H:%M",
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="reservation_time must use HH:MM format.",
        )

    reservation_id = uuid.uuid4()

    # --------------------------------------------------------
    # Check existing reservation
    # --------------------------------------------------------

    existing = session.execute(
        """
        SELECT reservation_id
        FROM reservations
        WHERE reservation_date = %s
        ALLOW FILTERING
        """,
        (
            reservation_date,
        ),
    )

    # --------------------------------------------------------
    # Simple learning-project availability rule.
    #
    # Later we can replace this with actual table/seat
    # allocation logic.
    # --------------------------------------------------------

    current_bookings = 0

    for row in existing:

        current_bookings += 1

    MAX_RESERVATIONS_PER_DAY = 20

    if current_bookings >= MAX_RESERVATIONS_PER_DAY:

        raise HTTPException(
            status_code=409,
            detail="No reservation capacity available for this date.",
        )

    session.execute(
        """
        INSERT INTO reservations (
            reservation_id,
            customer_name,
            phone,
            reservation_date,
            reservation_time,
            guests,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            reservation_id,
            request.customer_name,
            request.phone,
            reservation_date,
            request.reservation_time,
            request.guests,
            "CONFIRMED",
        ),
    )

    logger.info(
        "RESERVATION CREATED | reservation_id=%s",
        reservation_id,
    )

    return {
        "status": "CONFIRMED",
        "reservation_id": str(
            reservation_id
        ),
        "customer_name": request.customer_name,
        "date": request.reservation_date,
        "time": request.reservation_time,
        "guests": request.guests,
    }


# ============================================================
# GET RESERVATIONS
# ============================================================

@app.get("/api/reservations")
def get_reservations():

    rows = session.execute(
        """
        SELECT
            reservation_id,
            customer_name,
            phone,
            reservation_date,
            reservation_time,
            guests,
            status
        FROM reservations
        """
    )

    reservations = []

    for row in rows:

        reservations.append(
            {
                "reservation_id": str(
                    row.reservation_id
                ),
                "customer_name":
                    row.customer_name,
                "phone":
                    row.phone,
                "reservation_date":
                    str(row.reservation_date),
                "reservation_time":
                    row.reservation_time,
                "guests":
                    row.guests,
                "status":
                    row.status,
            }
        )

    return reservations


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "application":
            "Restaurant AI Agent",

        "llm":
            OLLAMA_MODEL,

        "ollama":
            OLLAMA_HOST,

        "database":
            "Cassandra",

        "rag":
            "PDF → chunks → Ollama embeddings → Cassandra → Ollama",
    }