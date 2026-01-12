"""
Paper Brain: Simplified Agent-Based arXiv Paper Discovery

Clean, minimal flow:
1. User query → Semantic rewrite → arXiv search (15 results)
2. ChromaDB ranking → Top 10 papers displayed
3. Agent loop (max 3 messages):
   - Tool: search_more_papers() - refine and search again
   - Tool: load_selected_papers() - load PDFs for RAG
4. Switch to Main RAG chat
"""

from typing import List, Optional
import requests
import feedparser
import asyncio
import time
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
import chromadb
from chromadb.utils.embedding_functions import GoogleGenerativeAiEmbeddingFunction
from dotenv import load_dotenv
import os
from .fetcher import ingest_arxiv_paper
from .rag import multi_paper_rag_with_documents

load_dotenv()


# =================
# STATE MANAGEMENT
# =================

class BrainState:
    """Global state for Paper Brain session."""
    
    def __init__(self):
        self.current_results = []           # Top 10 papers from last search
        self.last_semantic_query = ""       # Last semantic rewrite
        self.loaded_documents = []          # PDFs loaded for RAG
        self.message_count = 0              # User messages processed
        self.MAX_MESSAGES = 3               # Cost limit
    
    def add_results(self, papers: List[dict], semantic_query: str):
        """Store search results and the query used."""
        self.current_results = papers
        self.last_semantic_query = semantic_query
    
    def increment_messages(self):
        """Increment message counter."""
        self.message_count += 1
    
    def is_limit_reached(self) -> bool:
        """Check if message limit reached."""
        return self.message_count >= self.MAX_MESSAGES
    
    def get_selected_papers(self, indices: List[int]) -> List[dict]:
        """Get papers by display indices (1-based)."""
        return [self.current_results[i-1] for i in indices 
                if 1 <= i <= len(self.current_results)]


# Global state instance
state = BrainState()

# LLM instance (reused across functions)
llm = GoogleGenAI(model="models/gemini-2.5-flash-lite", temperature=0.1)


# ===============
# CORE FUNCTIONS
# ===============

async def semantic_rewrite(query: str) -> str:
    """
    Optimize user query for arXiv search using LLM.
    
    Args:
        query: Raw user query
        
    Returns:
        Optimized search string (concise, keyword-focused)
    """
    prompt = f"""You are a research paper search optimizer. Rewrite the user's query into an optimal arXiv search string.

CONSTRAINTS:
- Use technical terms and keywords
- use clean punctutation marks 
- Remove filler words (e.g., "papers about", "research on")
- Focus on core concepts
- Keep domain-specific terminology

USER QUERY: "{query}"

OUTPUT (search string only, no explanation):"""

    response = await llm.acomplete(prompt)
    optimized = str(response).strip().strip('"')
    
    print(f"🔄 Semantic rewrite: '{query}' → '{optimized}'")
    return optimized


async def search_and_display(semantic_query: str) -> str:
    """
    Search arXiv, rank by relevance, display top 10 papers.
    
    Args:
        semantic_query: Optimized search query
        
    Returns:
        Formatted display string with papers
    """
    # Step 1: Search arXiv API
    print(f"🔎 Searching arXiv for: {semantic_query}")
    
    base_url = 'http://export.arxiv.org/api/query'
    params = {
        'search_query': f'all:{semantic_query}',
        'start': 0,
        'max_results': 15,
        'sortBy': 'relevance',
        'sortOrder': 'descending'
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        
        if not feed.entries:
            return "❌ No papers found. Try a different query."
        
        # Extract paper data
        papers = []
        for entry in feed.entries:
            arxiv_id = entry.id.split('/abs/')[-1]
            papers.append({
                'title': entry.title.replace('\n', ' ').strip(),
                'abstract': entry.summary.replace('\n', ' ').strip(),
                'authors': ', '.join([a.name for a in entry.authors[:3]]),
                'arxiv_id': arxiv_id,
                'url': entry.link
            })
        
        print(f"📥 Fetched {len(papers)} papers from arXiv")
        
    except Exception as e:
        return f"❌ arXiv search failed: {e}"
    
    # Step 2: Rank by abstract similarity using ChromaDB
    try:
        print("📊 Ranking papers by relevance: ")
        
        # Create ephemeral collection
        client = chromadb.Client()
        google_ef = GoogleGenerativeAiEmbeddingFunction(
            api_key=os.getenv("GOOGLE_API_KEY"),
            model_name="models/text-embedding-004"
        )
        
        collection_name = f"papers_{int(time.time() * 1000000)}"
        collection = client.create_collection(
            name=collection_name,
            embedding_function=google_ef
        )
        
        # Add abstracts to collection
        for i, paper in enumerate(papers):
            collection.add(
                documents=[paper['abstract']],
                metadatas=[{'index': i}],
                ids=[f"paper_{i}"]
            )
        
        # Query for top 10 matches
        results = collection.query(
            query_texts=[semantic_query],
            n_results=min(10, len(papers))
        )
        
        # Build ranked list
        ranked = []
        for i, doc_id in enumerate(results['ids'][0]):
            idx = results['metadatas'][0][i]['index']
            paper = papers[idx].copy()
            paper['score'] = 1.0 - results['distances'][0][i]
            ranked.append(paper)
        
        # Store in state
        state.add_results(ranked, semantic_query)
        
        print(f"✓ Ranked and stored top {len(ranked)} papers")
        
    except Exception as e:
        return f"❌ Ranking failed: {e}"
    
    # Step 3: Format display
    output = f"\n{'═'*10}\n"
    output += f"{'TOP PAPERS':^10}\n"
    output += f"{'═'*10}\n\n"
    
    for i, paper in enumerate(ranked, 1):
        title = paper['title'][:75] + '...' if len(paper['title']) > 75 else paper['title']
        output += f"{i}.{title}\n"
        output += f"   Relevance:[{paper['score']:.3f}]\n"
        output += f"   Authors: {paper['authors']}\n"
        output += f"   arXiv: {paper['arxiv_id']}\n\n"
    
    output += f"{'─'*10}\n"
    output += f"Showing {len(ranked)} papers. You can:\n"
    output += f"  • Ask for more papers (agent will refine the search)\n"
    output += f"  • Select papers by number (e.g., '1,3,5')\n"
    
    return output


# =============
# AGENT TOOLS
# =============

async def search_more_papers() -> str:
    """
    Tool: Refine last query and search again.
    Agent calls this when user wants different/more results.
    
    Returns:
        New search results
    """
    if not state.last_semantic_query:
        return "❌ No previous search. Please start with a query."
    
    print(f"\n🔄 Refining previous search...")
    
    # Semantic rewrite the previous semantic query (refinement)
    refined_query = await semantic_rewrite(state.last_semantic_query)
    
    # Search and display
    return await search_and_display(refined_query)


def load_selected_papers(paper_numbers: str) -> str:
    """
    Tool: Load selected papers as PDFs for RAG.
    Agent calls this when user selects papers.
    
    Args:
        paper_numbers: Comma-separated indices (e.g., "1,3,5")
        
    Returns:
        Success/failure message
    """
    if not state.current_results:
        return "❌ No papers available. Search first."
    
    # Parse indices
    try:
        indices = [int(n.strip()) for n in paper_numbers.split(',')]
    except:
        return "❌ Invalid format. Use comma-separated numbers (e.g., '1,3,5')."
    
    selected = state.get_selected_papers(indices)
    
    if not selected:
        return "❌ No valid papers selected. Check the numbers."
    
    # Load PDFs
    print(f"\n{'─'*10}")
    print(f"📚 LOADING {len(selected)} PAPER(S)")
    print(f"{'─'*10}\n")
    
    all_documents = []
    
    for paper in selected:
        title = paper['title'][:60] + '...' if len(paper['title']) > 60 else paper['title']
        print(f"📥 {title} ", end='')
        
        try:
            documents = ingest_arxiv_paper(paper['title'])
            if documents:
                all_documents.extend(documents)
                print(f"✓ {len(documents)} pages")
            else:
                print("✗ Failed")
        except Exception as e:
            print(f"✗ Error: {str(e)[:40]}")
    
    if not all_documents:
        return "\n❌ Failed to load any papers. Try different selections."
    
    # Store in state
    state.loaded_documents = all_documents
    
    output = f"\n✓ Successfully loaded {len(all_documents)} pages from {len(selected)} paper(s)\n\n"
    output += f"{'='*80}\n"
    output += f"📚 Papers ready! Type 'switch' to move to RAG chat mode.\n"
    output += f"{'='*80}\n"
    
    return output


# ==================
# QUERY ROUTER
# ==================

async def route_user_query(user_input: str, papers_loaded: bool) -> dict:
    """
    LLM-based query router to classify user intent.
    Foolproof alternative to hardcoded string matching.
    
    Args:
        user_input: Raw user input
        papers_loaded: Whether papers are currently loaded
        
    Returns:
        {"action": "quit" | "switch" | "agent", "message": str}
    """
    prompt = f"""You are a query intent classifier for a research paper discovery system.

CONTEXT:
- Papers loaded: {papers_loaded}

USER INPUT: "{user_input}"

Classify the user's intent into ONE of these actions:

1. QUIT - User wants to exit/leave the system
   Examples: "quit", "exit", "goodbye", "I'm done", "stop"
   
2. SWITCH - User wants to switch to RAG chat mode (only valid if papers are loaded)
   Examples: "switch", "move to chat", "ask questions", "query papers"
   
3. AGENT - User wants to continue with paper search (select papers, search more, etc.)
   Examples: "select paper 2", "show more papers", "different results", any numbers

RULES:
- If papers_loaded is False and user says SWITCH-like intent, classify as AGENT (can't switch without papers)
- Be lenient with variations and typos
- Default to AGENT if unclear

RESPOND WITH ONLY ONE WORD: QUIT, SWITCH, or AGENT

CLASSIFICATION:"""

    try:
        response = await llm.acomplete(prompt)
        action = str(response).strip().upper()
        
        # Validate response
        if action not in ['QUIT', 'SWITCH', 'AGENT']:
            action = 'AGENT'  # Default to agent if invalid
        
        return {"action": action.lower()}
        
    except Exception as e:
        print(f"⚠️  Router error: {e}. Defaulting to agent.")
        return {"action": "agent"}


# ================
# AGENT INTERFACE
# ================

async def paper_brain_interface():
    """
    Main agent-driven interface with message limit.
    
    Returns:
        List[Document] if papers loaded, None otherwise
    """
    print(f"\n{'='*10}")
    print(f"{'PAPER BRAIN - INTELLIGENT PAPER DISCOVERY':^80}")
    print(f"{'='*10}\n")
    print("💡 How it works:")
    print("  1. Enter your research query")
    print("  2. Agent searches and shows top 10 papers")
    print("  3. You can ask for more papers or select papers to load")
    print(f"  4. Limit: {state.MAX_MESSAGES} messages (cost optimization)\n")
    print(f"{'─'*10}\n")
    
    # Get initial query
    initial_query = input("🔍 Enter your research query: ").strip()
    
    if not initial_query:
        print("❌ No query provided. Exiting.")
        return None
    
    # Initial search (semantic rewrite + search + display)
    print(f"\n{'─'*10}")
    semantic_query = await semantic_rewrite(initial_query)
    results = await search_and_display(semantic_query)
    print(results)
    
    # Create agent tools
    search_tool = FunctionTool.from_defaults(
        fn=search_more_papers,
        name="search_more_papers",
        description="Refine the previous search query and fetch new papers. Use when user asks for more papers, different results, or wants to see other research."
    )
    
    load_tool = FunctionTool.from_defaults(
        fn=load_selected_papers,
        name="load_selected_papers",
        description="Load selected papers by their display numbers (comma-separated). Use when user provides numbers like '1,3,5' or says 'select paper X'."
    )
    
    # Create agent with memory
    agent = ReActAgent(
        tools=[search_tool, load_tool],
        llm=llm,
        verbose=True,
        max_iterations=5
    )
    
    # Agent conversation loop
    while True:
        # Check message limit
        if state.is_limit_reached():
            print(f"\n{'⚠'*40}")
            print(f"⚠️  MESSAGE LIMIT REACHED ({state.MAX_MESSAGES} messages)")
            print(f"{'⚠'*10}\n")
            print("Please either:")
            print("  • Select papers to load (e.g., '1,2,3')")
            print("  • Type 'quit' to exit\n")
            
            final_input = input("💬 Your choice: ").strip()
            
            if final_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Exiting Paper Brain...")
                return None
            
            # Try to load papers
            try:
                result = load_selected_papers(final_input)
                print(result)
                
                if state.loaded_documents:
                    return state.loaded_documents
                else:
                    print("❌ Failed to load papers. Exiting.")
                    return None
            except:
                print("❌ Invalid input. Exiting.")
                return None
        
        # Get user input
        user_input = input("\n💬 You: ").strip()
        
        if not user_input:
            continue
        
        # Route query using LLM
        route = await route_user_query(user_input, bool(state.loaded_documents))
        
        # Handle routing decision
        if route["action"] == "quit":
            print("\n👋 Exiting Paper Brain...")
            return None
        
        elif route["action"] == "switch":
            if state.loaded_documents:
                print("\n✨ Switching to RAG chat...")
                return state.loaded_documents
            else:
                print("❌ No papers loaded yet. Select papers first.")
                continue
        
        # route["action"] == "agent" - continue to agent processing
        
        # Increment message count
        state.increment_messages()
        print(f"[Message {state.message_count}/{state.MAX_MESSAGES}]")
        
        # Agent processes input
        try:
            response = await agent.run(user_input)
            print(f"\n🤖 Assistant: {response}")
            
            # Check if papers loaded
            if state.loaded_documents:
                print("\n✨ Papers loaded! Type 'switch' to move to RAG chat.")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")


# =================
# MAIN ENTRY POINT
# =================

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
                print(f"\n{'─'*10}")
                print("ANSWER")
                print(f"{'─'*10}\n")
                print(str(response))
            except Exception as e:
                print(f"❌ Error: {e}")
