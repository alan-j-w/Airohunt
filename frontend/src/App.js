import React, { useEffect, useState } from "react";
import { useStore } from "./store";

import { PipelineToolbar } from "./toolbar";
import { PipelineUI } from "./ui";
import Dashboard from "./components/Dashboard";
import ProfileSettings from "./components/ProfileSettings";
import SettingsPanel from "./components/SettingsPanel";
import OnboardingWizard from "./components/OnboardingWizard";

function App() {
  const { 
    activeTab, 
    setActiveTab, 
    profile,
    fetchProfile, 
    fetchJobs, 
    loadPipeline,
    fetchSettings,
    fetchStartups,
    fetchResumes,
    fetchQueue,
    fetchMetrics,
    isLoading 
  } = useStore();

  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    const initData = async () => {
      await fetchProfile();
      await fetchSettings();
      await fetchJobs();
      await loadPipeline();
      await fetchStartups();
      await fetchResumes();
      await fetchQueue();
      await fetchMetrics();
    };
    initData();
  }, [fetchProfile, fetchJobs, loadPipeline, fetchSettings, fetchStartups, fetchResumes, fetchQueue, fetchMetrics]);

  // Trigger Onboarding modal if profile is new/empty
  useEffect(() => {
    if (!isLoading && profile && !profile.name) {
      setShowOnboarding(true);
    } else {
      setShowOnboarding(false);
    }
  }, [profile, isLoading]);

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col font-sans">
      
      {/* HEADER SECTION */}
      <header className="px-6 py-4 bg-slate-900 border-b border-cyan-500/30 flex items-center justify-between shadow-lg shadow-cyan-950/20">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-emerald-400 flex items-center justify-center font-black text-black text-xl shadow-md shadow-cyan-500/20">
            AH
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 to-emerald-400 bg-clip-text text-transparent">
              Airohunt
            </h1>
            <p className="text-xs text-slate-400 font-medium">Automated Job Hunting</p>
          </div>
        </div>

        {/* LOADING INDICATOR */}
        {isLoading && (
          <div className="flex items-center gap-2 bg-cyan-950/40 border border-cyan-800/40 px-3 py-1 rounded-full text-xs text-cyan-400 animate-pulse">
            <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping"></span>
            Syncing State...
          </div>
        )}

        {/* NAVIGATION TABS */}
        <nav className="flex gap-2">
          {[
            { id: "dashboard", label: "Jobs Dashboard" },
            { id: "canvas", label: "Automation Canvas" },
            { id: "profile", label: "Resume & Profile" },
            { id: "settings", label: "Settings" }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                px-5 py-2.5 rounded-xl font-semibold text-sm transition-all duration-300
                ${activeTab === tab.id 
                  ? "bg-cyan-500 text-black shadow-md shadow-cyan-500/25 hover:scale-105" 
                  : "bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white"
                }
              `}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      {/* MAIN CONTAINER CONTENT */}
      <main className="flex-1 flex flex-col">
        {activeTab === "dashboard" && <Dashboard />}

        {activeTab === "canvas" && (
          <div className="flex-1 flex flex-col">
            <div className="bg-slate-900 border-b border-slate-800 px-4 py-2 flex items-center justify-between">
              <span className="text-xs text-slate-400 font-semibold tracking-wider uppercase">Drag nodes to customize your flow</span>
            </div>
            <PipelineToolbar />
            
            <div className="flex-1 relative">
              <PipelineUI />
            </div>
          </div>
        )}

        {activeTab === "profile" && <ProfileSettings />}
        
        {activeTab === "settings" && <SettingsPanel />}
      </main>

      {/* FIRST TIME ONBOARDING MODAL OVERLAY */}
      {showOnboarding && (
        <OnboardingWizard onClose={() => setShowOnboarding(false)} />
      )}

    </div>
  );
}

export default App;