import React, { useState, useEffect } from "react";
import { useStore } from "../store";
import { 
  FaCog, 
  FaKey, 
  FaRobot, 
  FaDatabase, 
  FaLink, 
  FaCheckCircle, 
  FaTimesCircle, 
  FaSpinner,
  FaExclamationTriangle,
  FaTrash
} from "react-icons/fa";
import Swal from "sweetalert2";

const SettingsPanel = () => {
  const { 
    settings, 
    fetchSettings, 
    saveSettings, 
    testConnection,
    resetAllData,
    isLoading 
  } = useStore();

  const [provider, setProvider] = useState(settings.active_provider || "openai");
  const [openaiKey, setOpenaiKey] = useState(settings.openai_api_key || "");
  const [groqKey, setGroqKey] = useState(settings.groq_api_key || "");
  const [geminiKey, setGeminiKey] = useState(settings.gemini_api_key || "");
  const [ollamaUrl, setOllamaUrl] = useState(settings.ollama_url || "http://localhost:11434");

  // Sources toggles state
  const [sourceAdzuna, setSourceAdzuna] = useState(settings.source_adzuna);
  const [sourceJooble, setSourceJooble] = useState(settings.source_jooble);
  const [sourceManualImport, setSourceManualImport] = useState(settings.source_manual_import);
  const [sourceCompanyCareers, setSourceCompanyCareers] = useState(settings.source_company_careers);

  // Diagnostic state
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null); // success, failed, null

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  // Sync state when settings are loaded from backend
  useEffect(() => {
    setProvider(settings.active_provider || "openai");
    setOpenaiKey(settings.openai_api_key || "");
    setGroqKey(settings.groq_api_key || "");
    setGeminiKey(settings.gemini_api_key || "");
    setOllamaUrl(settings.ollama_url || "http://localhost:11434");
    setSourceAdzuna(settings.source_adzuna);
    setSourceJooble(settings.source_jooble);
    setSourceManualImport(settings.source_manual_import);
    setSourceCompanyCareers(settings.source_company_careers);
  }, [settings]);

  const handleSave = async (e) => {
    e.preventDefault();
    const updatedSettings = {
      active_provider: provider,
      openai_api_key: openaiKey,
      groq_api_key: groqKey,
      gemini_api_key: geminiKey,
      ollama_url: ollamaUrl,
      source_adzuna: sourceAdzuna,
      source_jooble: sourceJooble,
      source_manual_import: sourceManualImport,
      source_company_careers: sourceCompanyCareers
    };

    let activeKey = "";
    if (provider === "openai") activeKey = openaiKey;
    if (provider === "groq") activeKey = groqKey;
    if (provider === "gemini") activeKey = geminiKey;

    if (provider !== "ollama" && !activeKey.trim()) {
      Swal.fire({
        title: "Warning: Missing API Key",
        text: `You have selected ${provider.toUpperCase()} as your active AI provider, but you haven't entered an API key. Airohunt will run in Local Heuristic Fallback Mode without calling external AIs.`,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Save & Run Local Mode",
        cancelButtonText: "Cancel & Add Key",
        background: "#0f172a",
        color: "#fff",
        confirmButtonColor: "#06b6d4",
        cancelButtonColor: "#475569"
      }).then(async (result) => {
        if (result.isConfirmed) {
          await saveSettings(updatedSettings);
          Swal.fire({
            title: "Settings Saved!",
            text: "Running in Local Heuristic Mode (No API key).",
            icon: "success",
            background: "#0f172a",
            color: "#fff",
            confirmButtonColor: "#06b6d4"
          });
        }
      });
      return;
    }

    await saveSettings(updatedSettings);
    Swal.fire({
      title: "Settings Saved!",
      text: "Job sources and AI credentials synchronized.",
      icon: "success",
      background: "#0f172a",
      color: "#fff",
      confirmButtonColor: "#06b6d4"
    });
  };

  const handleTestConnection = async () => {
    let activeKey = "";
    if (provider === "openai") activeKey = openaiKey;
    if (provider === "groq") activeKey = groqKey;
    if (provider === "gemini") activeKey = geminiKey;

    if (provider !== "ollama" && !activeKey.trim()) {
      setTestResult("failed");
      Swal.fire({
        title: "API Key Required",
        text: `Please enter your ${provider.toUpperCase()} API key before testing the connection.`,
        icon: "warning",
        background: "#0f172a",
        color: "#fff",
        confirmButtonColor: "#06b6d4"
      });
      return;
    }

    setTesting(true);
    setTestResult(null);

    const { connected, reason } = await testConnection(provider, activeKey, ollamaUrl);
    setTesting(false);
    setTestResult(connected ? "success" : "failed");

    if (connected) {
      Swal.fire({
        title: "Connection Successful!",
        text: `Successfully validated connection to ${provider.toUpperCase()}`,
        icon: "success",
        background: "#0f172a",
        color: "#fff",
        confirmButtonColor: "#06b6d4"
      });
    } else {
      Swal.fire({
        title: "Connection Failed",
        text: `Reason: ${reason}`,
        icon: "error",
        background: "#0f172a",
        color: "#fff",
        confirmButtonColor: "#f43f5e"
      });
    }
  };

  const handleResetAllData = async () => {
    Swal.fire({
      title: "Delete All Data?",
      text: "This action is irreversible. All profile details, settings.json, pipelines, and saved jobs will be permanently deleted from your local files.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Yes, Delete Everything",
      cancelButtonText: "Cancel",
      background: "#0f172a",
      color: "#fff",
      confirmButtonColor: "#ef4444",
      cancelButtonColor: "#475569"
    }).then(async (result) => {
      if (result.isConfirmed) {
        try {
          const success = await resetAllData();
          if (success) {
            Swal.fire({
              title: "Data Wiped!",
              text: "Airohunt has been reset. Starting onboarding wizard...",
              icon: "success",
              background: "#0f172a",
              color: "#fff",
              confirmButtonColor: "#06b6d4"
            });
          }
        } catch (error) {
          Swal.fire({
            title: "Reset Failed",
            text: error.message || "Failed to reset data.",
            icon: "error",
            background: "#0f172a",
            color: "#fff",
            confirmButtonColor: "#f43f5e"
          });
        }
      }
    });
  };

  return (
    <div className="flex-1 bg-slate-950 p-6 md:p-10 overflow-y-auto">
      <div className="max-w-4xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* LEFT COLUMN: SOURCE CONFIGURATION */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-6">
            <h3 className="font-bold text-slate-200 text-base flex items-center gap-2 border-b border-slate-800 pb-3">
              <FaDatabase className="text-cyan-400" /> Active Job Sources
            </h3>
            
            <div className="space-y-4">
              <label className="flex items-center justify-between cursor-pointer p-3 bg-slate-950/40 rounded-xl border border-slate-800/80 hover:border-slate-800 transition-colors">
                <div>
                  <span className="text-xs font-bold text-slate-200 block">Adzuna Job Index</span>
                  <span className="text-[10px] text-slate-500">Free developer keys required</span>
                </div>
                <input 
                  type="checkbox" 
                  checked={sourceAdzuna}
                  onChange={(e) => setSourceAdzuna(e.target.checked)}
                  className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-cyan-500 w-4 h-4 cursor-pointer"
                />
              </label>

              <label className="flex items-center justify-between cursor-pointer p-3 bg-slate-950/40 rounded-xl border border-slate-800/80 hover:border-slate-800 transition-colors">
                <div>
                  <span className="text-xs font-bold text-slate-200 block">Jooble Job Index</span>
                  <span className="text-[10px] text-slate-500">Aggregated worldwide search</span>
                </div>
                <input 
                  type="checkbox" 
                  checked={sourceJooble}
                  onChange={(e) => setSourceJooble(e.target.checked)}
                  className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-cyan-500 w-4 h-4 cursor-pointer"
                />
              </label>

              <label className="flex items-center justify-between cursor-pointer p-3 bg-slate-950/40 rounded-xl border border-slate-800/80 hover:border-slate-800 transition-colors">
                <div>
                  <span className="text-xs font-bold text-slate-200 block">Startup Radar</span>
                  <span className="text-[10px] text-slate-500">Kerala & Remote product hubs</span>
                </div>
                <input 
                  type="checkbox" 
                  checked={sourceCompanyCareers}
                  onChange={(e) => setSourceCompanyCareers(e.target.checked)}
                  className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-cyan-500 w-4 h-4 cursor-pointer"
                />
              </label>

              <label className="flex items-center justify-between cursor-pointer p-3 bg-slate-950/40 rounded-xl border border-slate-800/80 hover:border-slate-800 transition-colors">
                <div>
                  <span className="text-xs font-bold text-slate-200 block">Offline Imports</span>
                  <span className="text-[10px] text-slate-500">Load jobs from imported_jobs.json</span>
                </div>
                <input 
                  type="checkbox" 
                  checked={sourceManualImport}
                  onChange={(e) => setSourceManualImport(e.target.checked)}
                  className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-cyan-500 w-4 h-4 cursor-pointer"
                />
              </label>
            </div>
            
            <p className="text-[10px] text-slate-500 leading-relaxed">
              Job discovery runs these sources concurrently in the background and dedupes the results before scoring.
            </p>
          </div>

          {/* Danger Zone Section */}
          <div className="bg-slate-900 border border-rose-950/80 rounded-3xl p-6 shadow-xl space-y-4">
            <h3 className="font-bold text-rose-400 text-sm flex items-center gap-2 border-b border-rose-950 pb-3">
              <FaTrash className="text-rose-500 text-xs" /> Danger Zone
            </h3>
            <p className="text-[10px] text-slate-500 leading-relaxed">
              Permanently wipe all profiles, API credentials, canvas pipelines, and matching jobs data from this computer.
            </p>
            <button
              type="button"
              onClick={handleResetAllData}
              className="w-full py-2.5 bg-rose-950/20 hover:bg-rose-950/60 border border-rose-900/40 hover:border-rose-600 rounded-xl text-xs font-black text-rose-300 hover:text-white transition-all duration-200"
            >
              Reset Agent & Delete Data
            </button>
          </div>
        </div>

        {/* RIGHT COLUMN: AI PROVIDER ENGINE */}
        <div className="lg:col-span-2 space-y-6">
          <form onSubmit={handleSave} className="bg-slate-900 border border-slate-800 rounded-3xl p-6 md:p-8 shadow-xl space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                <FaCog className="text-cyan-400 text-lg" /> AI Provider & Credentials
              </h2>
              <span className="text-[10px] bg-slate-950 border border-slate-800 px-2.5 py-1 rounded text-slate-400 font-bold uppercase tracking-wider">
                Model Failover Active
              </span>
            </div>

            {/* Warning Banner for Local Heuristic Fallback Mode */}
            {provider !== "ollama" && !(provider === "openai" ? openaiKey : provider === "groq" ? groqKey : geminiKey).trim() && (
              <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-2xl flex items-start gap-3">
                <FaExclamationTriangle className="text-amber-400 mt-0.5 flex-shrink-0 text-base animate-pulse" />
                <div className="space-y-1">
                  <h4 className="text-xs font-bold text-amber-300">Local Heuristic Fallback Mode Active</h4>
                  <p className="text-[10px] text-slate-400 leading-relaxed">
                    No API Key is entered for the selected provider (<strong>{provider.toUpperCase()}</strong>). 
                    Airohunt will process job matches, scam filters, and resume optimization using pre-seeded local algorithms instead of AI models.
                  </p>
                </div>
              </div>
            )}

            {/* PROVIDER SELECTOR */}
            <div>
              <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5 flex items-center gap-1">
                <FaRobot className="text-cyan-500 text-[10px]" /> Primary AI Provider
              </label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none cursor-pointer focus:border-cyan-500"
              >
                <option value="openai">OpenAI (GPT-4o-mini)</option>
                <option value="groq">Groq (Llama-3.1)</option>
                <option value="gemini">Google Gemini (Gemini 1.5 Flash)</option>
                <option value="ollama">Ollama (Local Llama3)</option>
              </select>
            </div>

            {/* DYNAMIC API KEYS INPUTS */}
            <div className="space-y-4">
              <div>
                <label className="text-slate-400 text-[10px] font-black uppercase tracking-wider block mb-1">OpenAI API Key</label>
                <div className="relative">
                  <FaKey className="absolute left-3 top-3.5 text-slate-500 text-xs" />
                  <input
                    type="password"
                    value={openaiKey}
                    onChange={(e) => setOpenaiKey(e.target.value)}
                    placeholder="sk-..."
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-9 pr-4 py-2.5 text-xs font-mono text-white focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 text-[10px] font-black uppercase tracking-wider block mb-1">Groq API Key</label>
                <div className="relative">
                  <FaKey className="absolute left-3 top-3.5 text-slate-500 text-xs" />
                  <input
                    type="password"
                    value={groqKey}
                    onChange={(e) => setGroqKey(e.target.value)}
                    placeholder="gsk_..."
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-9 pr-4 py-2.5 text-xs font-mono text-white focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 text-[10px] font-black uppercase tracking-wider block mb-1">Gemini API Key</label>
                <div className="relative">
                  <FaKey className="absolute left-3 top-3.5 text-slate-500 text-xs" />
                  <input
                    type="password"
                    value={geminiKey}
                    onChange={(e) => setGeminiKey(e.target.value)}
                    placeholder="AIzaSy..."
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-9 pr-4 py-2.5 text-xs font-mono text-white focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 text-[10px] font-black uppercase tracking-wider block mb-1">Ollama Connection URL (Local)</label>
                <div className="relative">
                  <FaLink className="absolute left-3 top-3.5 text-slate-500 text-xs" />
                  <input
                    type="text"
                    value={ollamaUrl}
                    onChange={(e) => setOllamaUrl(e.target.value)}
                    placeholder="http://localhost:11434"
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-9 pr-4 py-2.5 text-xs font-mono text-white focus:outline-none"
                  />
                </div>
              </div>
            </div>

            {/* DIAGNOSTIC PANEL */}
            <div className="p-4 bg-slate-950/40 border border-slate-800/80 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h4 className="text-xs font-black uppercase text-slate-400 tracking-wider">Diagnostic Connectivity Tool</h4>
                <p className="text-[10px] text-slate-500 mt-0.5">Test connection for the selected provider: {provider.toUpperCase()}</p>
              </div>

              <div className="flex items-center gap-3">
                {testing && (
                  <span className="text-xs text-cyan-400 flex items-center gap-1 font-bold">
                    <FaSpinner className="animate-spin" /> Ping test...
                  </span>
                )}
                {!testing && testResult === "success" && (
                  <span className="text-xs text-emerald-400 flex items-center gap-1 font-black">
                    <FaCheckCircle /> Connection OK!
                  </span>
                )}
                {!testing && testResult === "failed" && (
                  <span className="text-xs text-rose-400 flex items-center gap-1 font-black">
                    <FaTimesCircle /> Verification Failed
                  </span>
                )}
                
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={testing}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold text-white rounded-xl transition-all"
                >
                  Test Connection
                </button>
              </div>
            </div>

            {/* SAVE CONFIGS */}
            <div className="pt-2 flex justify-end">
              <button
                type="submit"
                disabled={isLoading}
                className="px-8 py-3 bg-gradient-to-r from-cyan-500 to-emerald-400 text-black font-black rounded-xl text-sm hover:scale-105 transition-transform shadow-lg shadow-cyan-500/10"
              >
                {isLoading ? "Saving Configurations..." : "Save Settings"}
              </button>
            </div>

          </form>
        </div>

      </div>
    </div>
  );
};

export default SettingsPanel;
