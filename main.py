"""
Main Entry Point: Paper Brain AI System

Run the complete paper discovery and RAG pipeline.
"""

import asyncio
from ai.brain import paper_brain_interface
from ai.rag import multi_paper_rag_with_documents


if __name__ == "__main__":
    # Run Paper Brain agent
    documents = asyncio.run(paper_brain_interface())
    
    if documents:
        # Switch to Main RAG
        print(f"\n{'='*80}")
        print(f"{'MAIN RAG CHAT - ASK QUESTIONS ABOUT YOUR PAPERS':^80}")
        print(f"{'='*80}\n")
        
        # RAG chat loop
        while True:
            query = input("\n📚 Ask about your papers (or 'quit'): ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Thanks for using Paper Brain!")
                break
            
            if not query:
                continue
            
            try:
                response = multi_paper_rag_with_documents(documents, query)
                print(f"\n{'─'*80}")
                print("ANSWER")
                print(f"{'─'*80}\n")
                print(str(response))
            except Exception as e:
                print(f"❌ Error: {e}")
