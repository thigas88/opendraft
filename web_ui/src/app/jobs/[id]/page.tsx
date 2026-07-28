"use client";

import { use, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { ArrowLeft, CheckCircle2, CircleDashed, Loader2, FileDown, AlertCircle, Play } from "lucide-react";
import ReactMarkdown from "react-markdown";

const fetcher = (url: string) => fetch(url).then((res) => {
  if (!res.ok) throw new Error("Job not found");
  return res.json();
});

function DraftViewer({ jobId }: { jobId: string }) {
  const { data, error } = useSWR(`http://localhost:8000/api/jobs/${jobId}/draft`, fetcher);
  
  if (error) return <div className="text-red-400 text-sm mt-4">Não foi possível carregar a pré-visualização.</div>;
  if (!data) return <div className="flex items-center space-x-2 text-neutral-400 mt-4"><Loader2 className="w-4 h-4 animate-spin" /> <span>Carregando rascunho...</span></div>;
  
  return (
    <div className="mt-8 bg-neutral-950 rounded-2xl border border-neutral-800 p-6 sm:p-8 max-h-[600px] overflow-y-auto custom-scrollbar prose prose-invert prose-indigo max-w-none">
      <ReactMarkdown>{data.content}</ReactMarkdown>
    </div>
  );
}

const PHASES = [
  { id: "research", label: "Pesquisa & Fontes" },
  { id: "structure", label: "Estrutura & Esboço" },
  { id: "citations", label: "Citações" },
  { id: "compose", label: "Escrita" },
  { id: "validate", label: "Validação & Revisão" },
  { id: "compile", label: "Compilação" },
  { id: "exporting", label: "Exportação" },
];

export default function JobTracker({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { id } = use(params);
  const [isResuming, setIsResuming] = useState(false);
  
  const { data: job, error, mutate } = useSWR(`http://localhost:8000/api/jobs/${id}`, fetcher, { 
    refreshInterval: (data) => (data?.status === 'completed' || data?.status === 'error') ? 0 : 2000 
  });
  
  const handleResume = async () => {
    setIsResuming(true);
    try {
      const res = await fetch(`http://localhost:8000/api/jobs/${id}/resume`, { method: "POST" });
      if (res.ok) {
        mutate();
      } else {
        alert("Não foi possível continuar. O arquivo de checkpoint não foi encontrado.");
      }
    } catch (err) {
      console.error(err);
    }
    setIsResuming(false);
  };
  
  const logEndRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [job?.progress_details?.activity_log]);

  if (error) return (
    <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center text-white p-4">
      <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
      <h2 className="text-xl font-semibold mb-2">Erro ao carregar projeto</h2>
      <p className="text-neutral-400 mb-6 text-center">O projeto solicitado não foi encontrado ou ocorreu um erro.</p>
      <button onClick={() => router.push("/")} className="px-6 py-2 bg-neutral-800 rounded-xl hover:bg-neutral-700 transition-colors">Voltar</button>
    </div>
  );
  
  if (!job) return (
    <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center text-white">
      <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
    </div>
  );

  const getPhaseStatus = (phaseId: string) => {
    if (job.status === 'completed') return 'done';
    if (job.status === 'error' && job.current_phase === phaseId) return 'error';
    
    const phaseIndex = PHASES.findIndex(p => p.id === phaseId);
    const currentIndex = PHASES.findIndex(p => p.id === job.current_phase);
    
    if (phaseIndex < currentIndex) return 'done';
    if (phaseIndex === currentIndex) return 'running';
    return 'pending';
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col items-center py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl w-full space-y-8">
        
        {/* Navigation & Header */}
        <div className="flex items-start justify-between">
          <button 
            onClick={() => router.push("/")}
            className="flex items-center text-sm font-medium text-neutral-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Voltar ao Dashboard
          </button>
          
          <div className="flex items-center space-x-2 bg-neutral-900 border border-neutral-800 px-3 py-1.5 rounded-lg text-xs font-medium">
            <span className={`w-2 h-2 rounded-full ${
              job.status === 'completed' ? 'bg-emerald-500' : 
              job.status === 'error' ? 'bg-red-500' : 'bg-amber-500 animate-pulse'
            }`} />
            <span className="capitalize text-neutral-300">{job.status}</span>
          </div>
        </div>

        <div className="space-y-2">
          <h1 className="text-2xl sm:text-3xl font-bold text-white line-clamp-2 leading-tight">
            {job.topic}
          </h1>
          <p className="text-neutral-500 text-sm">
            Nível: {job.level.replace("_", " ").toUpperCase()} • 
            Iniciado em {new Date(job.created_at).toLocaleString()}
          </p>
        </div>

        {/* Progress Tracker (Stepper) */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-6 sm:p-8">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between space-y-6 sm:space-y-0 relative">
            {/* Desktop connecting line */}
            <div className="hidden sm:block absolute top-1/2 left-0 w-full h-[2px] bg-neutral-800 -translate-y-1/2 z-0" />
            
            {PHASES.map((phase) => {
              const status = getPhaseStatus(phase.id);
              return (
                <div key={phase.id} className="relative z-10 flex sm:flex-col items-center space-x-4 sm:space-x-0 sm:space-y-3">
                  <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-2xl flex items-center justify-center border-2 transition-all duration-500 ${
                    status === 'done' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500 shadow-[0_0_20px_-5px_rgba(16,185,129,0.3)]' :
                    status === 'running' ? 'bg-indigo-500/20 border-indigo-500 text-indigo-400 shadow-[0_0_20px_-5px_rgba(99,102,241,0.5)]' :
                    status === 'error' ? 'bg-red-500/10 border-red-500/30 text-red-500' :
                    'bg-neutral-950 border-neutral-800 text-neutral-600'
                  }`}>
                    {status === 'done' ? <CheckCircle2 className="w-5 h-5" /> : 
                     status === 'running' ? <Loader2 className="w-5 h-5 animate-spin" /> : 
                     status === 'error' ? <AlertCircle className="w-5 h-5" /> :
                     <CircleDashed className="w-5 h-5" />}
                  </div>
                  <span className={`text-sm font-medium ${
                    status === 'done' ? 'text-neutral-300' :
                    status === 'running' ? 'text-indigo-400' :
                    status === 'error' ? 'text-red-400' : 'text-neutral-600'
                  }`}>
                    {phase.label}
                  </span>
                </div>
              );
            })}
          </div>
          
          {job.status === 'running' && (
            <div className="mt-8">
              <div className="h-2 w-full bg-neutral-950 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-indigo-500 transition-all duration-1000 ease-out rounded-full relative"
                  style={{ width: `${job.progress_percent || 0}%` }}
                >
                  <div className="absolute inset-0 bg-white/20 w-full animate-[shimmer_2s_infinite]" />
                </div>
              </div>
              <div className="text-right mt-2 text-xs font-medium text-neutral-500">
                {job.progress_percent || 0}% concluído
              </div>
            </div>
          )}
        </div>

        {/* Real-time Activity Log */}
        {job.status === 'running' && job.progress_details?.activity_log && (
          <div className="bg-neutral-900 border border-neutral-800 rounded-3xl p-6 sm:p-8">
            <h3 className="text-lg font-semibold text-white mb-6">Logs da Atividade</h3>
            <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-neutral-800">
              {job.progress_details.activity_log.map((log: any, idx: number) => (
                <div key={idx} className="flex items-start space-x-3 bg-neutral-950/50 p-3 rounded-xl border border-neutral-800/50 animate-in fade-in slide-in-from-bottom-2">
                  <span className="text-xl shrink-0 mt-0.5">{log.icon}</span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-neutral-200">{log.message}</p>
                    <p className="text-xs text-neutral-500 mt-1">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>
        )}

        {/* Results */}
        {job.status === 'completed' && (
          <div className="bg-neutral-900 border border-emerald-500/20 rounded-3xl p-6 sm:p-8 space-y-6">
            <div className="flex items-center space-x-3 text-emerald-400 mb-6">
              <CheckCircle2 className="w-8 h-8" />
              <h2 className="text-2xl font-bold">Pesquisa Concluída!</h2>
            </div>
            
            <div className="grid sm:grid-cols-2 gap-4">
              <a 
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  alert(`O arquivo DOCX foi salvo em: ${job.docx_path}`);
                }}
                className="flex items-center justify-center space-x-2 p-4 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded-2xl text-blue-400 font-medium transition-colors"
              >
                <FileDown className="w-5 h-5" />
                <span>Baixar formato Word (.docx)</span>
              </a>
              <a 
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  alert(`O arquivo PDF foi salvo em: ${job.pdf_path}`);
                }}
                className="flex items-center justify-center space-x-2 p-4 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-2xl text-red-400 font-medium transition-colors"
              >
                <FileDown className="w-5 h-5" />
                <span>Baixar formato PDF</span>
              </a>
            </div>
            
            <div className="mt-8 bg-neutral-950 border border-neutral-800 rounded-2xl p-6">
              <h3 className="text-sm font-semibold text-neutral-400 mb-4 uppercase tracking-wider">Caminhos Locais</h3>
              <div className="space-y-2 text-sm font-mono text-neutral-300">
                <p><span className="text-neutral-500">PDF:</span> {job.pdf_path}</p>
                <p><span className="text-neutral-500">DOCX:</span> {job.docx_path}</p>
              </div>
            </div>
            
            {/* Markdown Draft Preview */}
            <DraftViewer jobId={id} />
          </div>
        )}

        {job.status === 'error' && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-3xl p-6 sm:p-8 space-y-4">
            <div className="flex items-center space-x-3 text-red-400">
              <AlertCircle className="w-6 h-6" />
              <h2 className="text-xl font-bold">Falha na Geração</h2>
            </div>
            <p className="text-neutral-300 bg-red-500/5 p-4 rounded-xl border border-red-500/10 font-mono text-sm whitespace-pre-wrap">
              {job.error_message || "Ocorreu um erro desconhecido durante o processo."}
            </p>
            
            <button
              onClick={handleResume}
              disabled={isResuming}
              className="flex items-center justify-center space-x-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium transition-colors disabled:opacity-50"
            >
              {isResuming ? <Loader2 className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
              <span>Continuar de Onde Parou</span>
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
