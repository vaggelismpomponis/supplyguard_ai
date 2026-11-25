"""Setup script to install required dependencies"""
import subprocess
import sys

requirements = [
    "python-dotenv",
    "chromadb",
    "langchain",
    "langchain-neo4j",
    "langchain-anthropic",
    "neo4j",
]

print("Installing dependencies for Agentic RAG System...")
for req in requirements:
    print(f"  Installing {req}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", req])

print("\n✅ All dependencies installed!")
print("\nNext steps:")
print("1. Make sure Neo4j is running (check docker-compose.yml)")
print("2. Set up your .env file with:")
print("   - ANTHROPIC_API_KEY=your_key")
print("3. Run: python agentic_rag.py")
