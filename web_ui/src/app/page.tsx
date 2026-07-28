"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Loader2, Sparkles, BookOpen, Trash2 } from "lucide-react";
import useSWR from "swr";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function Home() {
  const [topic, setTopic] = useState("");
  const [level, setLevel] = useState("research_paper");
  const [citationStyle, setCitationStyle] = useState("abnt");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();

  const { data: jobs, error, mutate } = useSWR("http://localhost:8000/api/jobs", fetcher, { refreshInterval: 5000 });

  const handleDelete = async (e: React.MouseEvent, jobId: string) => {
    e.stopPropagation();
    if (!confirm("Tem certeza que deseja excluir esta pesquisa e todos os seus arquivos?")) return;
    
    try {
      await fetch(`http://localhost:8000/api/jobs/${jobId}`, { method: "DELETE" });
      mutate();
    } catch (err) {
      console.error("Erro ao excluir", err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;

    setIsSubmitting(true);
    try {
      const res = await fetch("http://localhost:8000/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, level, citation_style: citationStyle }),
      });
      const data = await res.json();
      router.push(`/jobs/${data.job_id}`);
    } catch (err) {
      console.error(err);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col items-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl w-full space-y-10">
        
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="flex items-center justify-center space-x-3 mb-6">
            <div className="p-3 bg-indigo-500/10 rounded-2xl border border-indigo-500/20">
              <Sparkles className="w-8 h-8 text-indigo-400" />
            </div>
            <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-br from-white to-neutral-500 bg-clip-text text-transparent">
              OpenDraft
            </h1>
          </div>
          <p className="text-lg text-neutral-400 max-w-2xl mx-auto">
            Gere rascunhos de pesquisas acadêmicas com citações reais, utilizando múltiplos agentes de IA.
          </p>
        </div>

        {/* Generate Card */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-8 shadow-2xl relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-b from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          
          <form onSubmit={handleSubmit} className="relative z-10 space-y-6">
            <div className="space-y-4">
              <label htmlFor="topic" className="block text-sm font-medium text-neutral-300">
                Tópico da Pesquisa
              </label>
              <textarea
                id="topic"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                rows={3}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl p-4 text-white placeholder-neutral-500 focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all resize-none"
                placeholder="Ex: O impacto das redes neurais convolucionais em diagnósticos oncológicos..."
                required
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-4">
                <label htmlFor="level" className="block text-sm font-medium text-neutral-300">
                  Nível Acadêmico
                </label>
                <select
                  id="level"
                  value={level}
                  onChange={(e) => setLevel(e.target.value)}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl p-4 text-white focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all appearance-none"
                >
                  <option value="research_paper">Artigo de Pesquisa</option>
                  <option value="bachelor">TCC (Bacharelado)</option>
                  <option value="master">Dissertação (Mestrado)</option>
                  <option value="phd">Tese (Doutorado)</option>
                </select>
              </div>

              <div className="space-y-4">
                <label htmlFor="citationStyle" className="block text-sm font-medium text-neutral-300">
                  Estilo de Formatação
                </label>
                <select
                  id="citationStyle"
                  value={citationStyle}
                  onChange={(e) => setCitationStyle(e.target.value)}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-2xl p-4 text-white focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all appearance-none"
                >
                  <option value="abnt">ABNT (Brasil)</option>
                  <option value="apa">APA (Internacional)</option>
                  <option value="ieee">IEEE (Exatas/Engenharia)</option>
                  <option value="mla">MLA (Humanidades)</option>
                  <option value="chicago">Chicago</option>
                  <option value="harvard">Harvard</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !topic.trim()}
              className="w-full py-4 px-6 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-all shadow-[0_0_40px_-10px_rgba(99,102,241,0.5)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Iniciando Pesquisa...</span>
                </>
              ) : (
                <>
                  <BookOpen className="w-5 h-5" />
                  <span>Gerar Rascunho Acadêmico</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* History */}
        <div className="space-y-6">
          <h2 className="text-xl font-semibold flex items-center text-neutral-300">
            <FileText className="w-5 h-5 mr-2 text-neutral-500" />
            Pesquisas Recentes
          </h2>
          
          {!jobs ? (
            <div className="flex justify-center p-8">
              <Loader2 className="w-8 h-8 text-neutral-600 animate-spin" />
            </div>
          ) : jobs.length === 0 ? (
            <div className="text-center py-12 bg-neutral-900/50 rounded-3xl border border-neutral-800/50 text-neutral-500">
              Nenhuma pesquisa gerada ainda.
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {jobs.map((job: any) => (
                <div
                  key={job.id}
                  onClick={() => router.push(`/jobs/${job.id}`)}
                  className="bg-neutral-900 border border-neutral-800 rounded-2xl p-5 hover:border-neutral-700 hover:bg-neutral-800/50 cursor-pointer transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider bg-neutral-800 px-2 py-1 rounded-md">
                        {job.level.replace("_", " ")}
                      </span>
                      <span className="flex items-center space-x-1.5">
                        <span className={`w-2 h-2 rounded-full ${
                          job.status === 'completed' ? 'bg-emerald-500' : 
                          job.status === 'error' ? 'bg-red-500' : 'bg-amber-500 animate-pulse'
                        }`} />
                        <span className="text-xs text-neutral-400 capitalize">{job.status}</span>
                      </span>
                    </div>
                    <p className="text-sm font-medium text-neutral-200 line-clamp-2 mt-3">
                      {job.topic}
                    </p>
                  </div>
                  
                  <div className="mt-4 pt-4 border-t border-neutral-800/50 flex items-center justify-between">
                    <span className="text-xs text-neutral-500">
                      {new Date(job.created_at).toLocaleDateString()}
                    </span>
                    <div className="flex items-center space-x-3">
                      <button 
                        onClick={(e) => handleDelete(e, job.id)}
                        className="text-neutral-500 hover:text-red-400 transition-colors p-1"
                        title="Excluir pesquisa"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <span className="text-xs font-medium text-indigo-400">
                        Ver detalhes &rarr;
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
