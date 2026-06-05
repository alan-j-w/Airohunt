import React, { useState } from "react";
import { useStore } from "../store";
import { 
  FaUser, 
  FaEnvelope, 
  FaPhone, 
  FaMapMarkerAlt, 
  FaDollarSign, 
  FaTags, 
  FaCloudUploadAlt,
  FaPlus,
  FaFileAlt,
  FaList,
  FaBrain
} from "react-icons/fa";
import Swal from "sweetalert2";

const ProfileSettings = () => {
  const { profile, saveProfile, uploadResume, resumes, saveResumes, fetchResumes, isLoading, errorMessage } = useStore();

  const [name, setName] = useState(profile.name || "");
  const [email, setEmail] = useState(profile.email || "");
  const [phone, setPhone] = useState(profile.phone || "");
  const [location, setLocation] = useState(profile.location || "");
  const [salary, setSalary] = useState(profile.salary_expectation || 0);
  const [resumeText, setResumeText] = useState(profile.base_resume || "");
  
  // New Onboarding preferences
  const [experienceLevel, setExperienceLevel] = useState(profile.experience_level || "Fresher");
  const [preferredWorkMode, setPreferredWorkMode] = useState(profile.preferred_work_mode || "Remote");
  const [region, setRegion] = useState(profile.region || "Kerala");
  const [aiInstructions, setAiInstructions] = useState(profile.ai_instructions || "");
  const [globalRules, setGlobalRules] = useState(profile.global_rules || "");
  const [temporarySearchRules, setTemporarySearchRules] = useState(profile.temporary_search_rules || "");
  const [preferredCompanyTypes, setPreferredCompanyTypes] = useState(profile.preferred_company_types || []);
  const [excludedCompanyTypes, setExcludedCompanyTypes] = useState(profile.excluded_company_types || []);
  const [newPrefCompanyInput, setNewPrefCompanyInput] = useState("");
  const [newExCompanyInput, setNewExCompanyInput] = useState("");
  
  // Specialized Resumes State
  const [activeVersion, setActiveVersion] = useState("react");
  const [localResumes, setLocalResumes] = useState({});
  const [newVerSkill, setNewVerSkill] = useState("");

  React.useEffect(() => {
    if (resumes && Object.keys(resumes).length > 0) {
      setLocalResumes(resumes);
    }
  }, [resumes]);
  
  // Chip tags state
  const [targetRoles, setTargetRoles] = useState(profile.target_roles || []);
  const [newRoleInput, setNewRoleInput] = useState("");
  const [skills, setSkills] = useState(profile.skills || []);
  const [newSkillInput, setNewSkillInput] = useState("");
  
  // Sync state if profile changes (e.g. after upload auto-fill)
  React.useEffect(() => {
    setName(profile.name || "");
    setEmail(profile.email || "");
    setPhone(profile.phone || "");
    setLocation(profile.location || "");
    setSalary(profile.salary_expectation || 0);
    setResumeText(profile.base_resume || "");
    setExperienceLevel(profile.experience_level || "Fresher");
    setPreferredWorkMode(profile.preferred_work_mode || "Remote");
    setRegion(profile.region || "Kerala");
    setAiInstructions(profile.ai_instructions || "");
    setGlobalRules(profile.global_rules || "");
    setTemporarySearchRules(profile.temporary_search_rules || "");
    setPreferredCompanyTypes(profile.preferred_company_types || []);
    setExcludedCompanyTypes(profile.excluded_company_types || []);
    setTargetRoles(profile.target_roles || []);
    setSkills(profile.skills || []);
  }, [profile]);

  const handleAddRole = (e) => {
    e.preventDefault();
    if (newRoleInput.trim() && !targetRoles.includes(newRoleInput.trim())) {
      setTargetRoles([...targetRoles, newRoleInput.trim()]);
      setNewRoleInput("");
    }
  };

  const handleRemoveRole = (role) => {
    setTargetRoles(targetRoles.filter(r => r !== role));
  };

  const handleAddSkill = (e) => {
    e.preventDefault();
    if (newSkillInput.trim() && !skills.includes(newSkillInput.trim())) {
      setSkills([...skills, newSkillInput.trim()]);
      setNewSkillInput("");
    }
  };

  const handleRemoveSkill = (skill) => {
    setSkills(skills.filter(s => s !== skill));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    const updatedProfile = {
      name,
      email,
      phone,
      location,
      target_roles: targetRoles,
      skills,
      salary_expectation: Number(salary),
      base_resume: resumeText,
      experience_level: experienceLevel,
      preferred_work_mode: preferredWorkMode,
      region: region,
      ai_instructions: aiInstructions,
      preferred_company_types: preferredCompanyTypes,
      excluded_company_types: excludedCompanyTypes,
      global_rules: globalRules,
      temporary_search_rules: temporarySearchRules
    };
    
    await saveProfile(updatedProfile);
    Swal.fire({
      title: "Profile Saved!",
      text: "Your core preferences and base resume have been synchronized successfully.",
      icon: "success",
      background: "#0f172a",
      color: "#fff",
      confirmButtonColor: "#06b6d4"
    });
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      Swal.fire({
        title: "File too large",
        text: "Please upload a file smaller than 5MB.",
        icon: "error"
      });
      return;
    }

    try {
      const msg = await uploadResume(file);
      Swal.fire({
        title: "Resume Parsed!",
        text: msg || "Skills and contact information have been auto-extracted.",
        icon: "success",
        background: "#0f172a",
        color: "#fff",
        confirmButtonColor: "#06b6d4"
      });
    } catch (err) {
      Swal.fire({
        title: "Parsing Error",
        text: err.message || "Failed to parse PDF file. Ensure it is not password protected.",
        icon: "error",
        background: "#0f172a",
        color: "#fff",
        confirmButtonColor: "#be123c"
      });
    }
  };

  return (
    <div className="flex-1 bg-slate-950 p-6 md:p-10 overflow-y-auto">
      <div className="max-w-4xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* LEFT COLUMN: RESUME UPLOADER ZONE */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl flex flex-col items-center text-center">
            <h3 className="font-bold text-slate-200 text-base mb-2">Upload Resume</h3>
            <p className="text-xs text-slate-400 mb-6">Upload PDF or Text format to auto-fill details</p>

            <label className="w-full flex flex-col items-center justify-center border-2 border-dashed border-slate-700 hover:border-cyan-500/80 bg-slate-950/40 rounded-2xl p-8 cursor-pointer group transition-colors duration-300">
              <FaCloudUploadAlt className="text-4xl text-slate-500 group-hover:text-cyan-400 mb-3 transition-colors" />
              <span className="text-xs text-slate-300 font-semibold group-hover:text-white">Choose a file</span>
              <span className="text-[10px] text-slate-500 mt-1">PDF or TXT up to 5MB</span>
              <input 
                type="file" 
                accept=".pdf,.txt" 
                onChange={handleFileUpload} 
                className="hidden" 
              />
            </label>

            {isLoading && (
              <div className="mt-4 flex items-center gap-2 text-xs text-cyan-400 animate-pulse font-medium">
                <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping"></span>
                Extracting PDF text...
              </div>
            )}

            {errorMessage && (
              <div className="mt-4 p-3 bg-rose-950/20 border border-rose-800/40 text-rose-400 rounded-xl text-[11px] leading-relaxed">
                {errorMessage}
              </div>
            )}

            <div className="mt-6 pt-6 border-t border-slate-800 w-full text-left space-y-3">
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <FaFileAlt className="text-slate-500 flex-shrink-0" />
                <span className="truncate max-w-[180px] font-semibold">{profile.name ? `${profile.name}_Resume.pdf` : "No resume uploaded"}</span>
              </div>
              <p className="text-[10px] text-slate-500 leading-normal">
                Auto-fill extracts name, email, phone, and standard coding skills automatically using local regex checks.
              </p>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: PREFERENCES & PROFILE FIELDS */}
        <div className="lg:col-span-2 space-y-6">
          <form onSubmit={handleSave} className="bg-slate-900 border border-slate-800 rounded-3xl p-6 md:p-8 shadow-xl space-y-6">
            <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2 pb-4 border-b border-slate-800">
              <FaUser className="text-cyan-400 text-lg" /> Candidate Preferences
            </h2>

            {/* GRID PROFILE INFO */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5">Full Name</label>
                <div className="relative">
                  <FaUser className="absolute left-3.5 top-3.5 text-slate-500 text-sm" />
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Jane Doe"
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white focus:outline-none transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5">Email Address</label>
                <div className="relative">
                  <FaEnvelope className="absolute left-3.5 top-3.5 text-slate-500 text-sm" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="jane.doe@example.com"
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white focus:outline-none transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5">Phone Number</label>
                <div className="relative">
                  <FaPhone className="absolute left-3.5 top-3.5 text-slate-500 text-sm" />
                  <input
                    type="text"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="123-456-7890"
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white focus:outline-none transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5">Location / Base Address</label>
                <div className="relative">
                  <FaMapMarkerAlt className="absolute left-3.5 top-3.5 text-slate-500 text-sm" />
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="e.g. Kochi, Kerala"
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white focus:outline-none transition-colors"
                  />
                </div>
              </div>

              {/* NEW PREFERENCES DROPDOWNS */}
              <div>
                <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5 flex items-center gap-1">
                  <FaList className="text-[9px] text-cyan-500" /> Experience Level
                </label>
                <select
                  value={experienceLevel}
                  onChange={(e) => setExperienceLevel(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none cursor-pointer focus:border-cyan-500"
                >
                  <option value="Fresher">Fresher (Entry Level)</option>
                  <option value="Experienced">Experienced</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5 flex items-center gap-1">
                  <FaList className="text-[9px] text-cyan-500" /> Preferred Work Mode
                </label>
                <select
                  value={preferredWorkMode}
                  onChange={(e) => setPreferredWorkMode(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none cursor-pointer focus:border-cyan-500"
                >
                  <option value="Remote">Remote</option>
                  <option value="Onsite">Onsite</option>
                  <option value="Hybrid">Hybrid</option>
                  <option value="Any">Any / Flex</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5">Target Job Region</label>
                <div className="relative">
                  <FaMapMarkerAlt className="absolute left-3.5 top-3.5 text-slate-500 text-sm" />
                  <input
                    type="text"
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                    placeholder="e.g. Kerala, India"
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white focus:outline-none transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5">Minimum Annual Salary Expectation ($)</label>
                <div className="relative">
                  <FaDollarSign className="absolute left-3.5 top-3.5 text-slate-500 text-sm" />
                  <input
                    type="number"
                    value={salary}
                    onChange={(e) => setSalary(e.target.value)}
                    placeholder="65000"
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white focus:outline-none transition-colors"
                  />
                </div>
              </div>
            </div>

            {/* AI FILTERING NATURAL LANGUAGE INSTRUCTIONS */}
            <div>
              <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5 flex items-center gap-1">
                <FaBrain className="text-cyan-500 text-xs" /> AI Search & Filtering Instructions (Natural Language preferences)
              </label>
              <textarea
                value={aiInstructions}
                onChange={(e) => setAiInstructions(e.target.value)}
                placeholder="Example: Only show fresher React, Django, or MERN stack jobs. Avoid training institutes, bond companies, placement consultancies. Prefer startups that test via practical tasks rather than DSA-heavy whiteboard interviews..."
                rows={4}
                className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-2xl p-4 text-xs text-slate-300 focus:outline-none resize-none transition-colors leading-relaxed"
              />
            </div>

            {/* TARGET ROLES TAG INPUT */}
            <div>
              <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5 flex items-center gap-1">
                <FaTags className="text-cyan-500 text-[10px]" /> Target Roles
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newRoleInput}
                  onChange={(e) => setNewRoleInput(e.target.value)}
                  placeholder="e.g. React Developer"
                  className="flex-1 bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-4 py-2 text-sm text-white focus:outline-none transition-colors"
                />
                <button
                  type="button"
                  onClick={handleAddRole}
                  className="px-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-cyan-500 rounded-xl text-xs font-bold text-white flex items-center gap-1 transition-all"
                >
                  <FaPlus /> Add
                </button>
              </div>
              <div className="flex flex-wrap gap-1.5 mt-2.5">
                {targetRoles.length === 0 ? (
                  <span className="text-xs text-slate-500 italic">No roles added yet.</span>
                ) : (
                  targetRoles.map((role) => (
                    <span key={role} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-950 border border-slate-800 text-xs text-slate-300 font-semibold rounded-lg">
                      {role}
                      <button type="button" onClick={() => handleRemoveRole(role)} className="text-slate-500 hover:text-rose-400 font-bold transition-colors">×</button>
                    </span>
                  ))
                )}
              </div>
            </div>

            {/* SKILLS TAG INPUT */}
            <div>
              <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5 flex items-center gap-1">
                <FaTags className="text-cyan-500 text-[10px]" /> Core Skills & Technologies
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newSkillInput}
                  onChange={(e) => setNewSkillInput(e.target.value)}
                  placeholder="e.g. React"
                  className="flex-1 bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-4 py-2 text-sm text-white focus:outline-none transition-colors"
                />
                <button
                  type="button"
                  onClick={handleAddSkill}
                  className="px-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-cyan-500 rounded-xl text-xs font-bold text-white flex items-center gap-1 transition-all"
                >
                  <FaPlus /> Add
                </button>
              </div>
              <div className="flex flex-wrap gap-1.5 mt-2.5">
                {skills.length === 0 ? (
                  <span className="text-xs text-slate-500 italic">No skills listed yet. Upload a resume or add custom tags.</span>
                ) : (
                  skills.map((skill) => (
                    <span key={skill} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-cyan-950/40 border border-cyan-800/40 text-xs text-cyan-400 font-bold rounded-lg">
                      {skill}
                      <button type="button" onClick={() => handleRemoveSkill(skill)} className="text-cyan-500 hover:text-rose-400 font-bold transition-colors">×</button>
                    </span>
                  ))
                )}
              </div>
            </div>

            {/* STRICT VALIDATION SETTINGS SECTION */}
            <div className="border-t border-slate-800 pt-6 space-y-6">
              <h3 className="text-base font-bold text-slate-200 flex items-center gap-2">
                <FaBrain className="text-cyan-400" /> Strict Job Validation Rules
              </h3>

              {/* GLOBAL & TEMPORARY RULES TEXTAREAS */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5">
                    Global Rules (Always Enforced)
                  </label>
                  <textarea
                    value={globalRules}
                    onChange={(e) => setGlobalRules(e.target.value)}
                    placeholder="e.g. Avoid 'No Freshers'. Do not want 'Placement Officer'. No training institutes."
                    rows={3}
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl p-3 text-xs text-slate-300 focus:outline-none resize-none transition-colors"
                  />
                </div>
                <div>
                  <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5">
                    Temporary Search Rules (Override/Campaign Specific)
                  </label>
                  <textarea
                    value={temporarySearchRules}
                    onChange={(e) => setTemporarySearchRules(e.target.value)}
                    placeholder="e.g. Avoid Bangalore. Only Kochi or remote."
                    rows={3}
                    className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl p-3 text-xs text-slate-300 focus:outline-none resize-none transition-colors"
                  />
                </div>
              </div>

              {/* PREFERRED & EXCLUDED COMPANY TYPES */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* PREFERRED COMPANY TYPES */}
                <div className="space-y-2">
                  <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1">
                    Preferred Company Types
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newPrefCompanyInput}
                      onChange={(e) => setNewPrefCompanyInput(e.target.value)}
                      placeholder="e.g. Startup, SaaS, FinTech"
                      className="flex-1 bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none transition-colors"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          if (newPrefCompanyInput.trim() && !preferredCompanyTypes.includes(newPrefCompanyInput.trim())) {
                            setPreferredCompanyTypes([...preferredCompanyTypes, newPrefCompanyInput.trim()]);
                            setNewPrefCompanyInput("");
                          }
                        }
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => {
                        if (newPrefCompanyInput.trim() && !preferredCompanyTypes.includes(newPrefCompanyInput.trim())) {
                          setPreferredCompanyTypes([...preferredCompanyTypes, newPrefCompanyInput.trim()]);
                          setNewPrefCompanyInput("");
                        }
                      }}
                      className="px-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-cyan-500 rounded-xl text-xs font-bold text-white flex items-center justify-center transition-all"
                    >
                      Add
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {preferredCompanyTypes.length === 0 ? (
                      <span className="text-[11px] text-slate-500 italic">None preferred. Matches baseline default.</span>
                    ) : (
                      preferredCompanyTypes.map((type) => (
                        <span key={type} className="inline-flex items-center gap-1.5 px-2 py-1 bg-emerald-950/40 border border-emerald-800/40 text-[10px] text-emerald-400 font-bold rounded-lg">
                          {type}
                          <button
                            type="button"
                            onClick={() => setPreferredCompanyTypes(preferredCompanyTypes.filter(t => t !== type))}
                            className="text-emerald-500 hover:text-rose-400 font-bold transition-colors"
                          >
                            ×
                          </button>
                        </span>
                      ))
                    )}
                  </div>
                </div>

                {/* EXCLUDED COMPANY TYPES */}
                <div className="space-y-2">
                  <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1">
                    Excluded Company Types
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newExCompanyInput}
                      onChange={(e) => setNewExCompanyInput(e.target.value)}
                      placeholder="e.g. Agency, Consultancy, Service"
                      className="flex-1 bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none transition-colors"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          if (newExCompanyInput.trim() && !excludedCompanyTypes.includes(newExCompanyInput.trim())) {
                            setExcludedCompanyTypes([...excludedCompanyTypes, newExCompanyInput.trim()]);
                            setNewExCompanyInput("");
                          }
                        }
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => {
                        if (newExCompanyInput.trim() && !excludedCompanyTypes.includes(newExCompanyInput.trim())) {
                          setExcludedCompanyTypes([...excludedCompanyTypes, newExCompanyInput.trim()]);
                          setNewExCompanyInput("");
                        }
                      }}
                      className="px-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-cyan-500 rounded-xl text-xs font-bold text-white flex items-center justify-center transition-all"
                    >
                      Add
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {excludedCompanyTypes.length === 0 ? (
                      <span className="text-[11px] text-slate-500 italic">None excluded.</span>
                    ) : (
                      excludedCompanyTypes.map((type) => (
                        <span key={type} className="inline-flex items-center gap-1.5 px-2 py-1 bg-rose-950/40 border border-rose-800/40 text-[10px] text-rose-400 font-bold rounded-lg">
                          {type}
                          <button
                            type="button"
                            onClick={() => setExcludedCompanyTypes(excludedCompanyTypes.filter(t => t !== type))}
                            className="text-rose-500 hover:text-rose-400 font-bold transition-colors"
                          >
                            ×
                          </button>
                        </span>
                      ))
                    )}
                  </div>
                </div>

              </div>
            </div>

            {/* BASE RESUME TEXT AREA */}
            <div>
              <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5">Base Resume Text Content</label>
              <textarea
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                placeholder="Paste the raw text of your resume here to enable keyword mapping and AI tailoring..."
                rows={8}
                className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-2xl p-4 text-xs font-mono text-slate-300 focus:outline-none resize-none transition-colors"
              />
            </div>

            {/* SAVE BUTTON */}
            <div className="pt-4 flex justify-end">
              <button
                type="submit"
                disabled={isLoading}
                className="px-8 py-3 bg-gradient-to-r from-cyan-500 to-emerald-400 text-black font-black rounded-xl text-sm shadow-lg shadow-cyan-500/10 hover:scale-105 transition-all"
              >
                {isLoading ? "Saving Profile..." : "Save Preferences"}
              </button>
            </div>

          </form>
        </div>

      </div>

      {/* FULL-WIDTH SECTION: SPECIALIZED RESUME PROFILES */}
      <div className="max-w-4xl mx-auto mt-8 bg-slate-900 border border-slate-800 rounded-3xl p-6 md:p-8 shadow-xl space-y-6">
        <div className="border-b border-slate-800 pb-4">
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <FaFileAlt className="text-cyan-400 text-lg" /> Specialized Resume Profiles
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Airohunt automatically chooses the best resume version depending on the matched job's required skills and title, before running resume tailoring.
          </p>
        </div>

        {/* PROFILE SELECTOR SUB-TABS */}
        <div className="flex flex-wrap gap-2">
          {Object.entries(localResumes).map(([key, value]) => (
            <button
              key={key}
              type="button"
              onClick={() => setActiveVersion(key)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all uppercase tracking-wider ${
                activeVersion === key
                  ? "bg-cyan-500 text-black shadow-md shadow-cyan-500/20"
                  : "bg-slate-950 text-slate-400 hover:bg-slate-800 hover:text-white"
              }`}
            >
              {value.name || key}
            </button>
          ))}
        </div>

        {localResumes[activeVersion] && (
          <div className="space-y-4 pt-2">
            {/* version skills tags */}
            <div>
              <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5 flex items-center gap-1">
                Targeting Skills / Key Match Tags
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newVerSkill}
                  onChange={(e) => setNewVerSkill(e.target.value)}
                  placeholder="e.g. Redux"
                  className="flex-1 max-w-xs bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-4 py-2 text-sm text-white focus:outline-none transition-colors"
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); const btn = document.getElementById('add-ver-skill-btn'); if (btn) btn.click(); } }}
                />
                <button
                  id="add-ver-skill-btn"
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    if (!newVerSkill.trim()) return;
                    const curSkills = localResumes[activeVersion].skills || [];
                    if (!curSkills.includes(newVerSkill.trim())) {
                      setLocalResumes({
                        ...localResumes,
                        [activeVersion]: {
                          ...localResumes[activeVersion],
                          skills: [...curSkills, newVerSkill.trim()]
                        }
                      });
                      setNewVerSkill("");
                    }
                  }}
                  className="px-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-cyan-500 rounded-xl text-xs font-bold text-white flex items-center gap-1 transition-all"
                >
                  <FaPlus /> Add Tag
                </button>
              </div>
              <div className="flex flex-wrap gap-1.5 mt-2.5">
                {(localResumes[activeVersion].skills || []).map((skill) => (
                  <span key={skill} className="inline-flex items-center gap-1 px-2.5 py-1 bg-cyan-950/40 border border-cyan-800/40 text-[10px] text-cyan-400 font-bold rounded-md">
                    {skill}
                    <button
                      type="button"
                      onClick={() => {
                        const curSkills = localResumes[activeVersion].skills || [];
                        setLocalResumes({
                          ...localResumes,
                          [activeVersion]: {
                            ...localResumes[activeVersion],
                            skills: curSkills.filter(s => s !== skill)
                          }
                        });
                      }}
                      className="ml-1 text-cyan-500 hover:text-rose-400 font-bold transition-colors"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            </div>

            {/* version resume text */}
            <div>
              <label className="text-slate-400 text-xs font-bold uppercase tracking-wider block mb-1.5">
                Resume Markdown Template
              </label>
              <textarea
                value={localResumes[activeVersion].resume_text || ""}
                onChange={(e) => {
                  setLocalResumes({
                    ...localResumes,
                    [activeVersion]: {
                      ...localResumes[activeVersion],
                      resume_text: e.target.value
                    }
                  });
                }}
                rows={12}
                className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-2xl p-4 text-xs font-mono text-slate-300 focus:outline-none resize-none transition-colors"
                placeholder="Paste the resume markdown text version here..."
              />
            </div>

            {/* SAVE VERSIONS BUTTON */}
            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={async () => {
                  await saveResumes(localResumes);
                  Swal.fire({
                    title: "Resume Profiles Saved!",
                    text: "Your specialized resume profiles are updated and synced.",
                    icon: "success",
                    background: "#0f172a",
                    color: "#fff",
                    confirmButtonColor: "#06b6d4"
                  });
                }}
                className="px-6 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-black font-black rounded-xl text-xs uppercase tracking-wider transition-all"
              >
                Save Resume Profiles
              </button>
            </div>
          </div>
        )}
      </div>

    </div>
  );
};

export default ProfileSettings;
