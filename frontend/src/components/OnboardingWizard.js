import React, { useState } from "react";
import { useStore } from "../store";
import { 
  FaUser, 
  FaMapMarkerAlt, 
  FaBriefcase, 
  FaCloudUploadAlt, 
  FaArrowRight
} from "react-icons/fa";
import Swal from "sweetalert2";

const OnboardingWizard = ({ onClose }) => {
  const { saveProfile, uploadResume, isLoading, errorMessage } = useStore();

  const [activeStep, setActiveStep] = useState("choice"); // choice, form, upload
  
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [experience, setExperience] = useState("Fresher");
  const [region, setRegion] = useState("Kerala, India");
  const [workMode, setWorkMode] = useState("Any");
  const [aiInstructions, setAiInstructions] = useState("");

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !role.trim()) {
      Swal.fire({
        title: "Missing Fields",
        text: "Please enter your name and target job role!",
        icon: "warning"
      });
      return;
    }

    const initialProfile = {
      name,
      email: "",
      phone: "",
      location: workMode === "Remote" ? "Remote" : region,
      target_roles: [role.trim()],
      skills: ["Git"], // base default
      salary_expectation: 0,
      base_resume: "",
      experience_level: experience,
      preferred_work_mode: workMode,
      region: region,
      ai_instructions: aiInstructions
    };

    await saveProfile(initialProfile);
    Swal.fire({
      title: "Welcome aboard!",
      text: "Profile initialized. Scanning live jobs matching your targets...",
      icon: "success",
      background: "#0f172a",
      color: "#fff",
      confirmButtonColor: "#06b6d4"
    });
    onClose();
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    try {
      await uploadResume(file);
      Swal.fire({
        title: "Resume Extracted!",
        text: "AI auto-filled your skills and profile settings. You are ready to start!",
        icon: "success",
        background: "#0f172a",
        color: "#fff",
        confirmButtonColor: "#06b6d4"
      });
      onClose();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="fixed inset-0 z-[99] bg-black/90 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-2xl p-6 md:p-10 shadow-2xl flex flex-col relative overflow-hidden">
        
        {/* Glow Effects */}
        <div className="absolute top-0 right-0 h-40 w-40 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 h-40 w-40 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>

        {/* STEP CHOICE */}
        {activeStep === "choice" && (
          <div className="space-y-8 text-center relative z-10">
            <div>
              <div className="h-12 w-12 rounded-2xl bg-gradient-to-tr from-cyan-500 to-emerald-400 flex items-center justify-center font-black text-black text-2xl mx-auto shadow-lg shadow-cyan-500/25 mb-4">
                AH
              </div>
              <h2 className="text-3xl font-black bg-gradient-to-r from-cyan-400 to-emerald-400 bg-clip-text text-transparent">
                Setup Your Job Search Agent
              </h2>
              <p className="text-sm text-slate-400 mt-2">Let Airohunt customize your matching pipeline and search startup pools.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              
              {/* CARD UPLOAD */}
              <button 
                onClick={() => setActiveStep("upload")}
                className="p-6 bg-slate-950/40 hover:bg-slate-950/90 border border-slate-800 hover:border-cyan-500/50 rounded-2xl flex flex-col items-center text-center group transition-all duration-300"
              >
                <div className="h-12 w-12 rounded-xl bg-cyan-950/60 border border-cyan-800/40 text-cyan-400 flex items-center justify-center text-xl mb-4 group-hover:scale-110 transition-transform">
                  <FaCloudUploadAlt />
                </div>
                <h3 className="font-bold text-slate-100 group-hover:text-cyan-400 transition-colors">Upload Resume PDF</h3>
                <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                  We will scan and parse your experience, auto-filling your profile parameters and target tech skills.
                </p>
              </button>

              {/* CARD MANUAL */}
              <button 
                onClick={() => setActiveStep("form")}
                className="p-6 bg-slate-950/40 hover:bg-slate-950/90 border border-slate-800 hover:border-emerald-500/50 rounded-2xl flex flex-col items-center text-center group transition-all duration-300"
              >
                <div className="h-12 w-12 rounded-xl bg-emerald-950/60 border border-emerald-800/40 text-emerald-400 flex items-center justify-center text-xl mb-4 group-hover:scale-110 transition-transform">
                  <FaUser />
                </div>
                <h3 className="font-bold text-slate-100 group-hover:text-emerald-400 transition-colors">Start Fresh / Manual</h3>
                <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                  Enter target roles, region, work mode, and natural-language filtering instructions directly.
                </p>
              </button>

            </div>
          </div>
        )}

        {/* STEP UPLOAD */}
        {activeStep === "upload" && (
          <div className="space-y-6 relative z-10 text-center">
            <div>
              <h2 className="text-2xl font-black text-slate-100">Upload Your Resume</h2>
              <p className="text-xs text-slate-400 mt-1">Upload a PDF or TXT file to start scanning.</p>
            </div>

            <label className="w-full flex flex-col items-center justify-center border-2 border-dashed border-slate-700 hover:border-cyan-500/80 bg-slate-950/40 rounded-2xl p-10 cursor-pointer group transition-colors">
              <FaCloudUploadAlt className="text-4xl text-slate-500 group-hover:text-cyan-400 mb-3" />
              <span className="text-xs text-slate-300 font-semibold">Choose Resume PDF</span>
              <span className="text-[10px] text-slate-500 mt-1">Max file size 5MB</span>
              <input 
                type="file" 
                accept=".pdf,.txt" 
                onChange={handleFileUpload} 
                className="hidden" 
              />
            </label>

            {isLoading && (
              <div className="flex items-center justify-center gap-2 text-xs text-cyan-400 animate-pulse font-medium">
                <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping"></span>
                AI extracting details...
              </div>
            )}

            {errorMessage && (
              <div className="p-3 bg-rose-950/20 border border-rose-800/40 text-rose-400 rounded-xl text-xs">
                {errorMessage}
              </div>
            )}

            <button 
              onClick={() => setActiveStep("choice")}
              className="text-xs text-slate-400 hover:text-white underline mt-2 block"
            >
              Go Back
            </button>
          </div>
        )}

        {/* STEP MANUAL FORM */}
        {activeStep === "form" && (
          <form onSubmit={handleFormSubmit} className="space-y-5 relative z-10">
            <div>
              <h2 className="text-2xl font-black text-slate-100">Configure Profile</h2>
              <p className="text-xs text-slate-400 mt-1">Set basic parameters for your job matching engine.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-slate-400 text-[10px] font-black uppercase tracking-wider block mb-1">First Name</label>
                <div className="relative">
                  <FaUser className="absolute left-3 top-3.5 text-slate-500 text-xs" />
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Jane"
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-9 pr-4 py-2 text-sm text-white focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 text-[10px] font-black uppercase tracking-wider block mb-1">Target Job Role</label>
                <div className="relative">
                  <FaBriefcase className="absolute left-3 top-3.5 text-slate-500 text-xs" />
                  <input
                    type="text"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    placeholder="e.g. Sales Executive or React Developer"
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-9 pr-4 py-2 text-sm text-white focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 text-[10px] font-black uppercase tracking-wider block mb-1">Experience Level</label>
                <select
                  value={experience}
                  onChange={(e) => setExperience(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none cursor-pointer"
                >
                  <option value="Fresher">Fresher (Entry Level)</option>
                  <option value="Experienced">Experienced</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 text-[10px] font-black uppercase tracking-wider block mb-1">Region</label>
                <div className="relative">
                  <FaMapMarkerAlt className="absolute left-3 top-3.5 text-slate-500 text-xs" />
                  <input
                    type="text"
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                    placeholder="e.g. Kerala, India"
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-9 pr-4 py-2 text-sm text-white focus:outline-none"
                  />
                </div>
              </div>

              <div className="md:col-span-2">
                <label className="text-slate-400 text-[10px] font-black uppercase tracking-wider block mb-1">Work Mode</label>
                <div className="grid grid-cols-4 gap-2">
                  {["Remote", "Onsite", "Hybrid", "Any"].map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => setWorkMode(mode)}
                      className={`py-2 rounded-xl text-xs font-bold transition-all border ${
                        workMode === mode 
                          ? "bg-cyan-500/20 border-cyan-500 text-cyan-400" 
                          : "bg-slate-950 border-slate-800 text-slate-400 hover:bg-slate-800"
                      }`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>

              <div className="md:col-span-2">
                <label className="text-slate-400 text-[10px] font-black uppercase tracking-wider block mb-1">
                  AI Filtering Instructions (Natural Language preferences)
                </label>
                <textarea
                  value={aiInstructions}
                  onChange={(e) => setAiInstructions(e.target.value)}
                  placeholder="e.g. Avoid training institutes and bond companies. Prefer startups that review GitHub projects instead of DSA tests..."
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl p-3 text-xs text-slate-300 focus:outline-none resize-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <button 
                type="button"
                onClick={() => setActiveStep("choice")}
                className="text-xs text-slate-400 hover:text-white underline"
              >
                Go Back
              </button>
              <button
                type="submit"
                className="px-6 py-2.5 bg-gradient-to-r from-cyan-500 to-emerald-400 text-black font-black rounded-xl text-xs flex items-center gap-1 hover:scale-105 transition-transform"
              >
                Save Preferences <FaArrowRight />
              </button>
            </div>
          </form>
        )}

      </div>
    </div>
  );
};

export default OnboardingWizard;
