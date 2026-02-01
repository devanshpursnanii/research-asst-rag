'use client';

import Link from 'next/link';
import { ArrowLeft, FileText, Search, MessageSquare, BarChart, Github, Mail, Linkedin } from 'lucide-react';

export default function About() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <Link
            href="/app"
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 w-fit"
          >
            <ArrowLeft className="h-4 w-4" />
            <span className="text-sm">Back to App</span>
          </Link>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-6 py-12">
        {/* Title */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-serif font-bold text-gray-900 mb-4">
            PaperStack
          </h1>
          <p className="text-lg text-gray-600">
            AI-powered research assistant with citation-grounded responses.
          </p>
        </div>

        {/* Value Proposition */}
        <section className="mb-12">
          <h2 className="text-2xl font-serif font-semibold text-gray-900 mb-4">
            What is PaperStack?
          </h2>
          <div className="space-y-3 text-gray-700 font-serif">
            <p>
              A production-grade system for searching academic papers, building knowledge bases, and querying them through citation-grounded AI. Combines intelligent discovery with retrieval-augmented generation for accurate, source-backed answers.
            </p>
            <p>
              The platform operates through two components:
            </p>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>PaperBrain</strong> — semantic paper discovery and ranking</li>
              <li><strong>PaperChat</strong> — citation-enforced Q&A over selected papers</li>
            </ul>
            <p>
              Every response is traceable to exact sources. No hallucinations, only auditable answers.
            </p>
          </div>
        </section>

        {/* How to Use */}
        <section className="mb-12">
          <h2 className="text-2xl font-serif font-semibold text-gray-900 mb-6">
            How to Use
          </h2>
          <div className="space-y-6">
            {/* Step 1 */}
            <div className="flex gap-4 items-start">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-gray-900 text-white flex items-center justify-center font-semibold">
                1
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Search className="h-5 w-5 text-gray-700" />
                  <h3 className="text-lg font-semibold text-gray-900">Search Papers</h3>
                </div>
                <p className="text-gray-700 font-serif">
                  Use PaperBrain to search arXiv. The AI semantically optimizes your query 
                  to find the most relevant papers. 3 searches per session.
                </p>
              </div>
            </div>

            {/* Step 2 */}
            <div className="flex gap-4 items-start">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-gray-900 text-white flex items-center justify-center font-semibold">
                2
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <FileText className="h-5 w-5 text-gray-700" />
                  <h3 className="text-lg font-semibold text-gray-900">Load Papers</h3>
                </div>
                <p className="text-gray-700 font-serif">
                  Select papers to analyze. Click "Load Selected Papers" to download 
                  and process them. PDFs are parsed and prepared for RAG.
                </p>
              </div>
            </div>

            {/* Step 3 */}
            <div className="flex gap-4 items-start">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-gray-900 text-white flex items-center justify-center font-semibold">
                3
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <MessageSquare className="h-5 w-5 text-gray-700" />
                  <h3 className="text-lg font-semibold text-gray-900">Chat with Papers</h3>
                </div>
                <p className="text-gray-700 font-serif">
                  Ask questions in PaperChat. The AI retrieves relevant sections and 
                  provides answers with citations. 5 messages per session.
                </p>
              </div>
            </div>

            {/* Step 4 */}
            <div className="flex gap-4 items-start">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-gray-900 text-white flex items-center justify-center font-semibold">
                4
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <BarChart className="h-5 w-5 text-gray-700" />
                  <h3 className="text-lg font-semibold text-gray-900">Track Activity</h3>
                </div>
                <p className="text-gray-700 font-serif">
                  Monitor loaded papers, quota usage, and session details in the 
                  Session Activity sidebar.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Technical Architecture */}
        <section className="mb-12">
          <h2 className="text-2xl font-serif font-semibold text-gray-900 mb-4">
            Technical Architecture
          </h2>
          
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <span className="text-gray-400">•</span> Mode-Based Paper Discovery
              </h3>
              <p className="text-gray-700 text-sm pl-5 font-serif">
                Title or topic-based arXiv search with ChromaDB semantic ranking. LLM query optimization for discovery, original query for scoring.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <span className="text-gray-400">•</span> Multi-Query Retrieval
              </h3>
              <p className="text-gray-700 text-sm pl-5 font-serif">
                2 semantic variations per query. Hybrid retrieval: vector search (text-embedding-004) + BM25 with reciprocal rank fusion.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <span className="text-gray-400">•</span> LLM Reranking & MMR
              </h3>
              <p className="text-gray-700 text-sm pl-5 font-serif">
                Top 20 chunks reranked by LLM. MMR (λ=0.85) balances relevance with cross-paper diversity. 18K token context window.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <span className="text-gray-400">•</span> Task-Aware Routing
              </h3>
              <p className="text-gray-700 text-sm pl-5 font-serif">
                Query classifier: QA, Explain, Summarize, or Compare. Tuned retrieval parameters and specialized prompts per task.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <span className="text-gray-400">•</span> Citation Tracking
              </h3>
              <p className="text-gray-700 text-sm pl-5 font-serif">
                Every chunk tagged with [Paper Title, Page X]. Citations panel for traceability. All operations logged per session.
              </p>
            </div>
          </div>
        </section>

        {/* Data Sources */}
        <section className="mb-12">
          <h2 className="text-2xl font-serif font-semibold text-gray-900 mb-4">
            arXiv
          </h2>
          <p className="text-gray-700 font-serif">
            All research papers are sourced from{' '}
            <a
              href="https://arxiv.org"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-900 underline hover:text-gray-700"
            >
              arXiv.org
            </a>
            , a free distribution service and open-access archive for scholarly articles. 
            arXiv is a service of Cornell University and is operated by Cornell Tech.
          </p>
        </section>

        {/* Technology */}
        <section className="mb-12">
          <h2 className="text-2xl font-serif font-semibold text-gray-900 mb-4">
            Technology Stack
          </h2>
          <p className="text-gray-700 mb-3 font-serif">
            FastAPI backend with LlamaIndex RAG. Google Gemini for generation, text-embedding-004 for embeddings, ChromaDB for vector search.
          </p>
          <ul className="list-disc pl-6 space-y-1 text-gray-700 text-sm font-serif">
            <li><strong>Backend:</strong> FastAPI + LlamaIndex</li>
            <li><strong>LLM:</strong> Google Gemini 2.5 Flash</li>
            <li><strong>Embeddings:</strong> text-embedding-004</li>
            <li><strong>Vector Store:</strong> ChromaDB</li>
            <li><strong>Frontend:</strong> Next.js + TypeScript + Tailwind</li>
          </ul>
        </section>

        {/* Open Source */}
        <section className="mb-12">
          <h2 className="text-2xl font-serif font-semibold text-gray-900 mb-4">
            Open Source
          </h2>
          <p className="text-gray-700 font-serif">
            Open source on{' '}
            <a
              href="https://github.com/devanshpursnanii/research-asst-rag"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-900 underline hover:text-gray-700"
            >
              GitHub
            </a>
            . Contributions welcome.
          </p>
        </section>

        {/* Developer Badge */}
        <section className="mt-16 pt-8 border-t border-gray-200">
          <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl p-8 shadow-lg">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-serif font-bold text-white mb-2">Devansh Pursnani</h2>
              <p className="text-gray-300 text-sm font-serif max-w-2xl mx-auto">
                Computer science engineering student working on applied AI projects, with a focus on language models, retrieval systems, and research automation.
              </p>
            </div>
            
            <div className="flex items-center justify-center gap-4">
              <a
                href="https://github.com/devanshpursnanii"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors text-white text-sm font-medium"
              >
                <Github className="h-4 w-4" />
                <span>GitHub</span>
              </a>
              <a
                href="mailto:devansh.pursnani23@spit.ac.in"
                className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors text-white text-sm font-medium"
              >
                <Mail className="h-4 w-4" />
                <span>Email</span>
              </a>
              <a
                href="https://www.linkedin.com/in/devansh-pursnani-946853231/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors text-white text-sm font-medium"
              >
                <Linkedin className="h-4 w-4" />
                <span>LinkedIn</span>
              </a>
            </div>
          </div>
        </section>
        
        {/* Footer */}
        <div className="text-center text-sm text-gray-500 pt-8">
          <p className="font-serif">© 2026 PaperStack</p>
        </div>
      </main>
    </div>
  );
}
