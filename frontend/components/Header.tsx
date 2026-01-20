import { Github, FileText, Info, ScrollText } from 'lucide-react';

export default function Header() {
  return (
    <header className="border-b border-gray-200 bg-white px-6 py-4">
      <div className="flex items-center justify-between relative">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gray-900">
            <FileText className="h-5 w-5 text-white" />
          </div>
        </div>

        {/* Centered Title */}
        <h1 className="absolute left-1/2 -translate-x-1/2 text-xl font-semibold text-gray-900">PaperStack</h1>

        {/* Links */}
        <nav className="flex items-center gap-6">
          <a
            href="https://github.com/devanshpursnanii/research-asst-rag"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
          >
            <Github className="h-4 w-4" />
            <span>GitHub</span>
          </a>
          <a
            href="/logs"
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
          >
            <ScrollText className="h-4 w-4" />
            <span>Logs</span>
          </a>
          <a
            href="/about"
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
          >
            <Info className="h-4 w-4" />
            <span>About</span>
          </a>
        </nav>
      </div>
    </header>
  );
}
