from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_markdown_docs(folder: Path) -> list[Document]:
    """A minimal loader: one Document per file, real path kept as metadata."""
    return [
        Document(page_content=path.read_text(encoding="utf-8"), metadata={"source": str(path)})
        for path in sorted(folder.glob("*.md"))
    ]


docs = load_markdown_docs(Path(__file__).parent / "docs")
print(f"Loaded {len(docs)} document(s) from {docs[0].metadata['source']}")

splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=40)
chunks = splitter.split_documents(docs)

print(f"Split into {len(chunks)} chunks:\n")
for i, chunk in enumerate(chunks):
    print(f"--- chunk {i} ({len(chunk.page_content)} chars) ---")
    print(chunk.page_content)
    print()
