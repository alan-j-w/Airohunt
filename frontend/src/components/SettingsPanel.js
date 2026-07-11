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

  // Pipeline filter & weights states
  const [minMatchPercent, setMinMatchPercent] = useState(settings.min_match_percent ?? 50.0);
  const [minSalary, setMinSalary] = useState(settings.min_salary ?? 3.0);
  const [salaryCurrency, setSalaryCurrency] = useState(settings.salary_currency ?? "INR_LPA");
  const [salaryUnknownPolicy, setSalaryUnknownPolicy] = useState(settings.salary_unknown_policy ?? "Allow");
  const [scamMode, setScamMode] = useState(settings.scam_mode ?? "balanced");
  const [startupW, setStartupW] = useState(settings.startup_w ?? "Medium");
  const [remoteW, setRemoteW] = useState(settings.remote_w ?? "Medium");
  const [salaryW, setSalaryW] = useState(settings.salary_w ?? "Medium");
  const [trustW, setTrustW] = useState(settings.trust_w ?? "Medium");
  const [automationMode, setAutomationMode] = useState(settings.automation_mode ?? "Assisted Apply");

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
    setMinMatchPercent(settings.min_match_percent ?? 50.0);
    setMinSalary(settings.min_salary ?? 3.0);
    setSalaryCurrency(settings.salary_currency ?? "INR_LPA");
    setSalaryUnknownPolicy(settings.salary_unknown_policy ?? "Allow");
    setScamMode(settings.scam_mode ?? "balanced");
    setStartupW(settings.startup_w ?? "Medium");
    setRemoteW(settings.remote_w ?? "Medium");
    setSalaryW(settings.salary_w ?? "Medium");
    setTrustW(settings.trust_w ?? "Medium");
    setAutomationMode(settings.automation_mode ?? "Assisted Apply");
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
      source_company_careers: sourceCompanyCareers,
      min_match_percent: minMatchPercent,
      min_salary: minSalary,
      salary_currency: salaryCurrency,
      salary_unknown_policy: salaryUnknownPolicy,
      scam_mode: scamMode,
      startup_w: startupW,
      remote_w: remoteW,
      salary_w: salaryW,
      trust_w: trustW,
      automation_mode: automationMode
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

            {/* INGESTION & PIPELINE CONFIGURATION */}
            <div className="border-t border-slate-800 pt-6 space-y-6">
              <h3 className="font-bold text-slate-200 text-base border-b border-slate-800 pb-3 flex items-center gap-2">
                <FaRobot className="text-cyan-400" /> Strict Ingestion Pipeline & Scoring
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Min Match Percent */}
                <div>
                  <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5">
                    Min Skill Match Alignment: <span className="text-cyan-400 font-extrabold">{minMatchPercent}%</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={minMatchPercent}
                    onChange={(e) => setMinMatchPercent(parseFloat(e.target.value))}
                    className="w-full h-1.5 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                  />
                  <p className="text-[10px] text-slate-500 mt-1">Jobs scoring below this skill compatibility matching threshold are discarded on fetch.</p>
                </div>

                {/* Scam Detection Level */}
                <div>
                  <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5">
                    Scam Detection Mode
                  </label>
                  <select
                    value={scamMode}
                    onChange={(e) => setScamMode(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none cursor-pointer focus:border-cyan-500"
                  >
                    <option value="strict">Strict (Instantly discard all suspected scams)</option>
                    <option value="balanced">Balanced (Ingest but flag with warning metrics)</option>
                    <option value="off">Off (Disable AI scam scanner)</option>
                  </select>
                </div>

                {/* Min Salary & Currency */}
                <div className="space-y-3 md:col-span-2">
                  <span className="text-slate-400 text-xs font-bold uppercase tracking-wider block">
                    Salary Filter Requirements
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="text-slate-500 text-[10px] font-bold block mb-1">Minimum Value</label>
                      <input
                        type="number"
                        min="0"
                        value={minSalary}
                        onChange={(e) => setMinSalary(parseFloat(e.target.value))}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                    <div>
                      <label className="text-slate-500 text-[10px] font-bold block mb-1">Currency Format</label>
                      <select
                        value={salaryCurrency}
                        onChange={(e) => setSalaryCurrency(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-xs text-white focus:outline-none cursor-pointer focus:border-cyan-500"
                      >
                        <option value="INR_LPA">INR (Lakhs Per Annum)</option>
                        <option value="USD">USD ($ Per Annum)</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-slate-500 text-[10px] font-bold block mb-1">Unknown Salary Policy</label>
                      <select
                        value={salaryUnknownPolicy}
                        onChange={(e) => setSalaryUnknownPolicy(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-xs text-white focus:outline-none cursor-pointer focus:border-cyan-500"
                      >
                        <option value="Allow">Allow (Import anyway)</option>
                        <option value="Warn">Warn (Import with warnings)</option>
                        <option value="Hide">Hide (Discard if undisclosed)</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Opportunity Scoring Priority Weights */}
                <div className="md:col-span-2 space-y-3">
                  <span className="text-slate-400 text-xs font-bold uppercase tracking-wider block">
                    Opportunity Scoring Priority Weights
                  </span>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div>
                      <label className="text-slate-500 text-[10px] font-bold block mb-1">Startup Weight</label>
                      <select
                        value={startupW}
                        onChange={(e) => setStartupW(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none cursor-pointer focus:border-cyan-500"
                      >
                        <option value="High">High</option>
                        <option value="Medium">Medium</option>
                        <option value="Low">Low</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-slate-500 text-[10px] font-bold block mb-1">Remote Weight</label>
                      <select
                        value={remoteW}
                        onChange={(e) => setRemoteW(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none cursor-pointer focus:border-cyan-500"
                      >
                        <option value="High">High</option>
                        <option value="Medium">Medium</option>
                        <option value="Low">Low</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-slate-500 text-[10px] font-bold block mb-1">Salary Weight</label>
                      <select
                        value={salaryW}
                        onChange={(e) => setSalaryW(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none cursor-pointer focus:border-cyan-500"
                      >
                        <option value="High">High</option>
                        <option value="Medium">Medium</option>
                        <option value="Low">Low</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-slate-500 text-[10px] font-bold block mb-1">Trust Weight</label>
                      <select
                        value={trustW}
                        onChange={(e) => setTrustW(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none cursor-pointer focus:border-cyan-500"
                      >
                        <option value="High">High</option>
                        <option value="Medium">Medium</option>
                        <option value="Low">Low</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Submission Engine Mode */}
                <div className="md:col-span-2">
                  <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5">
                    Application submission automation mode
                  </label>
                  <select
                    value={automationMode}
                    onChange={(e) => setAutomationMode(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none cursor-pointer focus:border-cyan-500"
                  >
                    <option value="Assisted Apply">Assisted Apply (Prefills form & generates console scripts)</option>
                    <option value="Disabled">Disabled (Direct manual apply only)</option>
                  </select>
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
