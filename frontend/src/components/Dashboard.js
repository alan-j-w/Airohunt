import React, { useState, useEffect } from "react";
import { useStore } from "../store";
import {
  FaBuilding,
  FaMapMarkerAlt,
  FaDollarSign,
  FaExternalLinkAlt,
  FaExclamationTriangle,
  FaCheckCircle,
  FaFileAlt,
  FaCopy,
  FaSearch,
  FaCheck,
  FaFilter,
  FaShieldAlt,
  FaRocket
} from "react-icons/fa";
import Swal from "sweetalert2";

const Dashboard = () => {
  const {
    jobs,
    fetchJobs,
    updateQueueStatus,
    applyJob,
    startups,
    fetchStartups,
    scrapeMoreStartups,
    isLoadingMoreStartups,
    metrics,
    fetchMetrics,
    fetchQueue,
    scrapeMoreJobs,
    isLoadingMore,
    validationReport,
    fetchValidationReport,
    activeFilters,
    filterOptions,
    fetchFilterOptions,
    updateFilter,
    resetFilters
  } = useStore();

  const [selectedJobId, setSelectedJobId] = useState(null);
  const [hideScams, setHideScams] = useState(false);
  const [activeFilterStatus, setActiveFilterStatus] = useState("Matched"); // Matched, Prepared, Queue, All
  const [showResumeModal, setShowResumeModal] = useState(false);
  const [showMetricsModal, setShowMetricsModal] = useState(false);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [showTierC, setShowTierC] = useState(false);
  const [copied, setCopied] = useState(false);
  const [copiedScript, setCopiedScript] = useState(false);

  const [currentPage, setCurrentPage] = useState(1);
  const jobsPerPage = 5;

  const [currentStartupPage, setCurrentStartupPage] = useState(1);
  const startupsPerPage = 3;

  // Search states for Indeed-style search bar
  const [searchQueryInput, setSearchQueryInput] = useState("");
  const [searchLocationInput, setSearchLocationInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchLocation, setSearchLocation] = useState("");

  useEffect(() => {
    fetchJobs();
    fetchStartups();
    fetchMetrics();
    fetchQueue();
    fetchValidationReport();
    fetchFilterOptions();
  }, [fetchJobs, fetchStartups, fetchMetrics, fetchQueue, fetchValidationReport, fetchFilterOptions]);

  // Set default selected job with Indeed search criteria
  const filteredJobs = jobs.filter(job => {
    const scamMatch = hideScams ? !job.is_scam : true;
    let statusMatch = true;
    if (activeFilterStatus === "Matched") {
      statusMatch = job.status === "Matched" || !job.status;
    } else if (activeFilterStatus === "Prepared") {
      statusMatch = job.status === "Prepared";
    } else if (activeFilterStatus === "Queue") {
      statusMatch = ["Applied", "Interviewing", "Ghosted", "Rejected", "Offered"].includes(job.status);
    }

    // Search query matching (Indeed behavior)
    let queryMatch = true;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const titleMatch = job.title?.toLowerCase().includes(q);
      const companyMatch = job.company?.toLowerCase().includes(q);
      const descMatch = job.description?.toLowerCase().includes(q);
      const skillMatch = job.skills_required?.some(s => s.toLowerCase().includes(q));
      queryMatch = titleMatch || companyMatch || descMatch || skillMatch;
    }

    let locationMatch = true;
    if (searchLocation.trim()) {
      const loc = searchLocation.toLowerCase();
      locationMatch = job.location?.toLowerCase().includes(loc);
    }

    return scamMatch && statusMatch && queryMatch && locationMatch;
  });

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setSearchQuery(searchQueryInput);
    setSearchLocation(searchLocationInput);
    
    if (searchQueryInput.trim() || searchLocationInput.trim()) {
      handleSearchScrape(searchQueryInput, searchLocationInput);
    }
  };

  const handleSearchScrape = async (keywords, location) => {
    Swal.fire({
      title: "Searching Online",
      text: `Fetching and analyzing jobs for "${keywords}" in "${location || 'Remote'}"...`,
      icon: "info",
      showConfirmButton: false,
      allowOutsideClick: false,
      background: "#0f172a",
      color: "#fff",
      didOpen: () => {
        Swal.showLoading();
      }
    });

    try {
      const success = await scrapeMoreJobs(keywords, location);
      Swal.close();
      if (success) {
        Swal.fire({
          toast: true,
          position: 'top-end',
          icon: 'success',
          title: `Found new jobs for "${keywords}"!`,
          showConfirmButton: false,
          timer: 3000,
          background: "#0f172a",
          color: "#fff"
        });
      } else {
        Swal.fire({
          title: "Search Completed",
          text: "No new matching jobs were discovered online. Check your API settings or try again.",
          icon: "info",
          background: "#0f172a",
          color: "#fff",
          confirmButtonColor: "#06b6d4"
        });
      }
    } catch (err) {
      console.error(err);
      Swal.close();
    }
  };

  const handleClearSearch = () => {
    setSearchQueryInput("");
    setSearchLocationInput("");
    setSearchQuery("");
    setSearchLocation("");
  };

  useEffect(() => {
    if (filteredJobs.length > 0) {
      const currentExists = filteredJobs.some(j => j.id === selectedJobId);
      if (!currentExists) {
        setSelectedJobId(filteredJobs[0].id);
      }
    } else {
      setSelectedJobId(null);
    }
  }, [filteredJobs, selectedJobId]);

  useEffect(() => {
    setCurrentPage(1);
  }, [activeFilterStatus, hideScams, searchQuery, searchLocation]);

  const totalPages = Math.ceil(filteredJobs.length / jobsPerPage);

  useEffect(() => {
    if (currentPage > totalPages && totalPages > 0) {
      setCurrentPage(totalPages);
    }
  }, [filteredJobs, currentPage, totalPages]);

  const totalStartupPages = Math.ceil(startups.length / startupsPerPage);

  useEffect(() => {
    if (currentStartupPage > totalStartupPages && totalStartupPages > 0) {
      setCurrentStartupPage(totalStartupPages);
    }
  }, [startups, currentStartupPage, totalStartupPages]);

  const indexOfLastJob = currentPage * jobsPerPage;
  const indexOfFirstJob = indexOfLastJob - jobsPerPage;
  const currentJobs = filteredJobs.slice(indexOfFirstJob, indexOfLastJob);

  const selectedJob = jobs.find(j => j.id === selectedJobId) || filteredJobs[0] || null;

  const handleVerifyCompany = (companyName) => {
    const query = `${companyName} legit reviews Glassdoor LinkedIn`;
    window.open(`https://www.google.com/search?q=${encodeURIComponent(query)}`, "_blank");
  };

  const handleApply = async (jobId) => {
    if (!jobId) return;

    const profile = useStore.getState().profile;
    if (!profile.base_resume || profile.base_resume.trim() === "") {
      Swal.fire({
        title: "Missing Resume",
        text: "Please paste your base resume in the Resume & Profile tab first before applying!",
        icon: "warning",
        background: "#0f172a",
        color: "#fff",
        confirmButtonColor: "#06b6d4"
      });
      return;
    }

    try {
      const res = await applyJob(jobId);
      if (res && res.tailored_resume) {
        setShowResumeModal(true);
        Swal.fire({
          toast: true,
          position: 'top-end',
          icon: 'success',
          title: 'Resume tailored and application prepared!',
          showConfirmButton: false,
          timer: 3000,
          background: "#0f172a",
          color: "#fff"
        });
      }
    } catch (error) {
      console.error(error);
    }
  };

  const handleLoadMore = async () => {
    try {
      const success = await scrapeMoreJobs(searchQuery, searchLocation);
      if (success) {
        Swal.fire({
          toast: true,
          position: 'top-end',
          icon: 'success',
          title: 'Discovered and analyzed new relevant jobs!',
          showConfirmButton: false,
          timer: 3000,
          background: "#0f172a",
          color: "#fff"
        });
      } else {
        Swal.fire({
          title: "Scraping Failed",
          text: "Unable to find additional jobs at the moment. Check your API settings or try again later.",
          icon: "error",
          background: "#0f172a",
          color: "#fff",
          confirmButtonColor: "#06b6d4"
        });
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleLoadMoreStartups = async () => {
    try {
      const success = await scrapeMoreStartups();
      if (success) {
        Swal.fire({
          toast: true,
          position: 'top-end',
          icon: 'success',
          title: 'Discovered new hiring startups!',
          showConfirmButton: false,
          timer: 3000,
          background: "#0f172a",
          color: "#fff"
        });
      } else {
        Swal.fire({
          title: "Discovery Failed",
          text: "Unable to find additional startups. Check your API settings or try again.",
          icon: "error",
          background: "#0f172a",
          color: "#fff",
          confirmButtonColor: "#06b6d4"
        });
      }
    } catch (err) {
      console.error(err);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const copyScriptToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedScript(true);
    setTimeout(() => setCopiedScript(false), 2000);
  };

  // Get Match Score Color
  const getScoreColor = (score) => {
    if (score >= 80) return "text-emerald-400 border-emerald-500/30 bg-emerald-500/10";
    if (score >= 50) return "text-amber-400 border-amber-500/30 bg-amber-500/10";
    return "text-rose-400 border-rose-500/30 bg-rose-500/10";
  };

  const getTierStars = (tier) => {
    switch (tier) {
      case "A": return "★★★★★";
      case "B": return "★★★★☆";
      case "C": return "★★★☆☆";
      default: return "☆☆☆☆☆";
    }
  };

  const getTierBorderClass = (tier, isSelected) => {
    if (isSelected) return "border-cyan-500 bg-slate-800/80 shadow-lg shadow-cyan-950/20";
    switch (tier) {
      case "A": return "border-emerald-500/30 hover:border-emerald-400 bg-emerald-950/5 hover:bg-emerald-950/10";
      case "B": return "border-blue-500/30 hover:border-blue-400 bg-blue-950/5 hover:bg-blue-950/10";
      case "C": return "border-slate-800/80 hover:border-slate-700 bg-slate-900/10 hover:bg-slate-900/20";
      default: return "border-slate-800 bg-slate-900/30";
    }
  };

  const renderJobCard = (job) => {
    const isSelected = selectedJobId === job.id;
    return (
      <div
        key={job.id}
        onClick={() => setSelectedJobId(job.id)}
        className={`p-3 rounded-xl border transition-all duration-200 cursor-pointer ${getTierBorderClass(job.validation_tier, isSelected)}`}
      >
        <div className="flex justify-between items-start gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className={`text-[8px] px-1.5 py-0.5 rounded font-black tracking-wider border ${job.validation_tier === 'A' ? 'bg-emerald-950/60 border-emerald-800/80 text-emerald-400' :
                job.validation_tier === 'B' ? 'bg-blue-950/60 border-blue-800/80 text-blue-400' :
                  'bg-slate-950/60 border-slate-800 text-slate-400'
                }`}>
                {getTierStars(job.validation_tier)} Tier {job.validation_tier}
              </span>
            </div>
            <h3 className="font-bold text-slate-200 text-xs md:text-sm leading-tight truncate mt-1.5">{job.title}</h3>
            <p className="text-[10px] text-slate-400 font-semibold mt-1 flex items-center gap-1 truncate">
              <FaBuilding className="text-slate-500" /> {job.company}
            </p>
          </div>
          <div className={`px-2 py-0.5 rounded-full border text-[9px] font-black tracking-wider uppercase ${getScoreColor(job.match_score)}`}>
            {job.match_score}%
          </div>
        </div>

        <div className="flex flex-wrap gap-x-2 gap-y-1 mt-2 text-[10px] text-slate-400 justify-between items-center">
          <span className="truncate max-w-[100px] flex items-center gap-0.5"><FaMapMarkerAlt className="text-slate-500" /> {job.location}</span>
          <span className="text-slate-500 text-[9px]">Conf: <span className="text-slate-300 font-bold">{job.validation_confidence || 0}%</span></span>
        </div>

        {job.is_scam && (
          <div className="mt-2 px-2 py-1 bg-rose-950/20 border border-rose-900/40 rounded-lg text-[9px] text-rose-400 font-bold flex items-center gap-1">
            <FaExclamationTriangle /> Warning: Scam Signal
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex-1 flex flex-col bg-slate-950 overflow-hidden" style={{ height: "calc(100vh - 73px)" }}>

      {/* INDEED-STYLE SEARCH BAR HEADER */}
      <div className="bg-slate-900 border-b border-slate-800 px-6 py-4 flex flex-col md:flex-row gap-4 items-center justify-center shadow-lg shadow-slate-950/40 relative z-10">
        <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row items-center w-full max-w-4xl bg-slate-950/80 border border-slate-800/80 rounded-xl overflow-hidden shadow-inner p-1 gap-1.5 md:gap-0">
          
          {/* WHAT INPUT */}
          <div className="flex items-center flex-1 w-full px-3 py-2 border-b md:border-b-0 md:border-r border-slate-800/80 gap-2">
            <FaSearch className="text-slate-400 text-sm flex-shrink-0" />
            <div className="flex-1">
              <label className="text-[8px] font-black uppercase text-slate-500 block leading-none mb-0.5">What</label>
              <input
                type="text"
                placeholder="Job title, keywords, or company"
                value={searchQueryInput}
                onChange={(e) => setSearchQueryInput(e.target.value)}
                className="w-full bg-transparent text-sm text-slate-200 placeholder-slate-600 focus:outline-none font-medium"
              />
            </div>
            {searchQueryInput && (
              <button 
                type="button" 
                onClick={() => setSearchQueryInput("")}
                className="text-slate-500 hover:text-slate-300 text-xs font-bold px-1"
              >
                ×
              </button>
            )}
          </div>

          {/* WHERE INPUT */}
          <div className="flex items-center flex-1 w-full px-3 py-2 gap-2">
            <FaMapMarkerAlt className="text-slate-400 text-sm flex-shrink-0" />
            <div className="flex-1">
              <label className="text-[8px] font-black uppercase text-slate-500 block leading-none mb-0.5">Where</label>
              <input
                type="text"
                placeholder="City, state, or 'Remote'"
                value={searchLocationInput}
                onChange={(e) => setSearchLocationInput(e.target.value)}
                className="w-full bg-transparent text-sm text-slate-200 placeholder-slate-600 focus:outline-none font-medium"
              />
            </div>
            {searchLocationInput && (
              <button 
                type="button" 
                onClick={() => setSearchLocationInput("")}
                className="text-slate-500 hover:text-slate-300 text-xs font-bold px-1"
              >
                ×
              </button>
            )}
          </div>

          {/* FIND JOBS BUTTON */}
          <button
            type="submit"
            className="w-full md:w-auto px-6 py-3 md:py-2.5 bg-gradient-to-r from-cyan-500 to-emerald-400 hover:from-cyan-400 hover:to-emerald-300 text-black font-black rounded-lg text-xs tracking-wider uppercase flex items-center justify-center gap-1.5 shadow-md shadow-cyan-500/10 active:scale-95 transition-all flex-shrink-0"
          >
            Find Jobs
          </button>
        </form>

        {/* Clear search states */}
        {(searchQuery || searchLocation) && (
          <button
            type="button"
            onClick={handleClearSearch}
            className="text-xs text-rose-400 hover:text-rose-300 font-bold uppercase tracking-wider transition-colors px-3 py-2 rounded-lg border border-rose-900/40 bg-rose-950/15"
          >
            Clear Search
          </button>
        )}
      </div>

      {/* THREE PANE LAYOUT */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">

        {/* LEFT PANE: JOBS LIST (3/12 width) */}
        <div className="w-full lg:w-3/12 border-r border-slate-800 flex flex-col bg-slate-900/40">

        {/* FILTER TOOLBAR */}
        <div className="p-4 border-b border-slate-800 bg-slate-900/60 flex flex-col gap-3">
          <div className="flex items-center justify-between flex-wrap gap-y-1.5">
            <h2 className="font-bold text-sm text-slate-300 tracking-wider uppercase">Listings Pool</h2>
            <div className="flex gap-2">
              <button
                onClick={() => { useStore.getState().fetchValidationReport(); setShowValidationModal(true); }}
                className="text-[10px] text-indigo-400 hover:text-indigo-300 font-bold uppercase tracking-wider transition-colors"
              >
                Validation Report
              </button>
              <button
                onClick={() => { fetchMetrics(); setShowMetricsModal(true); }}
                className="text-[10px] text-emerald-400 hover:text-emerald-300 font-bold uppercase tracking-wider transition-colors"
              >
                Metrics & Logs
              </button>
              <button
                onClick={() => { fetchJobs(); fetchStartups(); }}
                className="text-[10px] text-cyan-400 hover:text-cyan-300 font-bold uppercase tracking-wider transition-colors"
              >
                Sync
              </button>
            </div>
          </div>

          <div className="flex flex-wrap gap-1">
            {["Matched", "Prepared", "Queue", "All"].map((status) => (
              <button
                key={status}
                onClick={() => setActiveFilterStatus(status)}
                className={`px-2.5 py-1.5 rounded-lg text-[10px] font-black tracking-wider uppercase transition-all ${activeFilterStatus === status
                  ? "bg-cyan-500 text-black shadow-sm"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
                  }`}
              >
                {status}
              </button>
            ))}
          </div>

          <label className="flex items-center gap-2 cursor-pointer mt-1">
            <input
              type="checkbox"
              checked={hideScams}
              onChange={(e) => setHideScams(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-cyan-500 w-3.5 h-3.5 cursor-pointer"
            />
            <span className="text-[10px] font-bold text-amber-400 flex items-center gap-1">
              <FaFilter className="text-[9px]" /> Hide Suspected Scams
            </span>
          </label>
        </div>

        {/* SMART JOB FILTERS TOOLBAR */}
        <div className="px-4 py-3 border-b border-slate-800 bg-slate-900/40 flex flex-col gap-2">
          {/* Header & Reset */}
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-black uppercase text-slate-400 tracking-wider flex items-center gap-1">
              <FaFilter className="text-cyan-400" /> Smart Filters
            </span>
            <button
              onClick={() => resetFilters()}
              className="text-[9px] text-rose-400 hover:text-rose-300 font-black uppercase tracking-wider transition-colors"
            >
              Reset All
            </button>
          </div>

          {/* Grid of filters */}
          <div className="grid grid-cols-2 gap-2 text-[10px]">
            {/* Experience Dropdown */}
            <div>
              <label className="text-[8px] font-bold text-slate-500 uppercase block mb-0.5">Experience</label>
              <select
                value={activeFilters.experience_levels[0] || "All"}
                onChange={(e) => {
                  const val = e.target.value;
                  updateFilter("experience_levels", val === "All" ? [] : [val]);
                }}
                className="w-full bg-slate-950 border border-slate-850 hover:border-slate-700 rounded-lg text-slate-300 p-1.5 focus:outline-none focus:border-cyan-500 cursor-pointer"
              >
                <option value="All">All Experience</option>
                <option value="Fresher">Fresher (0 yr)</option>
                <option value="0-1 Years">0-1 Years</option>
                <option value="1-2 Years">1-2 Years</option>
                <option value="2-5 Years">2-5 Years</option>
                <option value="5+ Years">5+ Years</option>
              </select>
            </div>

            {/* Company Type Dropdown */}
            <div>
              <label className="text-[8px] font-bold text-slate-500 uppercase block mb-0.5">Company Type</label>
              <select
                value={activeFilters.company_types[0] || "All"}
                onChange={(e) => {
                  const val = e.target.value;
                  updateFilter("company_types", val === "All" ? [] : [val]);
                }}
                className="w-full bg-slate-950 border border-slate-850 hover:border-slate-700 rounded-lg text-slate-300 p-1.5 focus:outline-none focus:border-cyan-500 cursor-pointer"
              >
                <option value="All">All Types</option>
                <option value="Startup">Startup</option>
                <option value="Mid-size Product">Mid-size Product</option>
                <option value="Enterprise">Enterprise</option>
                <option value="MNC">MNC</option>
                <option value="Agency">Agency</option>
                <option value="Consultancy">Consultancy</option>
              </select>
            </div>

            {/* Salary Preset Dropdown */}
            <div>
              <label className="text-[8px] font-bold text-slate-500 uppercase block mb-0.5">Min Salary</label>
              <select
                value={activeFilters.min_salary || "All"}
                onChange={(e) => {
                  const val = e.target.value;
                  updateFilter("min_salary", val === "All" ? null : parseInt(val));
                }}
                className="w-full bg-slate-950 border border-slate-850 hover:border-slate-700 rounded-lg text-slate-300 p-1.5 focus:outline-none focus:border-cyan-500 cursor-pointer"
              >
                <option value="All">Any Salary</option>
                <option value="3">3+ LPA</option>
                <option value="5">5+ LPA</option>
                <option value="8">8+ LPA</option>
                <option value="12">12+ LPA</option>
                <option value="15">15+ LPA</option>
              </select>
            </div>

            {/* Latest Posted Dropdown */}
            <div>
              <label className="text-[8px] font-bold text-slate-500 uppercase block mb-0.5">Posted Within</label>
              <select
                value={activeFilters.posted_within_days || "All"}
                onChange={(e) => {
                  const val = e.target.value;
                  updateFilter("posted_within_days", val === "All" ? null : parseInt(val));
                }}
                className="w-full bg-slate-950 border border-slate-855 hover:border-slate-700 rounded-lg text-slate-300 p-1.5 focus:outline-none focus:border-cyan-500 cursor-pointer"
              >
                <option value="All">Any Time</option>
                <option value="1">Last 24 Hours</option>
                <option value="3">Last 3 Days</option>
                <option value="7">Last 7 Days</option>
                <option value="30">Last 30 Days</option>
              </select>
            </div>

            {/* Fresher Compatibility Dropdown */}
            <div>
              <label className="text-[8px] font-bold text-slate-500 uppercase block mb-0.5">Fresher Match</label>
              <select
                value={activeFilters.fresher_compatibility || "All"}
                onChange={(e) => {
                  updateFilter("fresher_compatibility", e.target.value);
                }}
                className="w-full bg-slate-950 border border-slate-850 hover:border-slate-700 rounded-lg text-slate-300 p-1.5 focus:outline-none focus:border-cyan-500 cursor-pointer"
              >
                <option value="All">All Roles</option>
                <option value="90%+">90%+ Match</option>
                <option value="75%+">75%+ Match</option>
                <option value="50%+">50%+ Match</option>
              </select>
            </div>

            {/* Source Dropdown */}
            <div>
              <label className="text-[8px] font-bold text-slate-500 uppercase block mb-0.5">Job Source</label>
              <select
                value={activeFilters.sources[0] || "All"}
                onChange={(e) => {
                  const val = e.target.value;
                  updateFilter("sources", val === "All" ? [] : [val]);
                }}
                className="w-full bg-slate-950 border border-slate-850 hover:border-slate-700 rounded-lg text-slate-300 p-1.5 focus:outline-none focus:border-cyan-500 cursor-pointer"
              >
                <option value="All">All Sources</option>
                {(filterOptions.sources || []).map(src => (
                  <option key={src} value={src}>{src}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Location Multi-Select Dropdown with Pills */}
          <div className="text-[10px]">
            <label className="text-[8px] font-bold text-slate-500 uppercase block mb-0.5">Locations</label>
            <select
              value=""
              onChange={(e) => {
                const val = e.target.value;
                if (val && !activeFilters.locations.includes(val)) {
                  updateFilter("locations", [...activeFilters.locations, val]);
                }
              }}
              className="w-full bg-slate-950 border border-slate-850 hover:border-slate-700 rounded-lg text-slate-300 p-1.5 focus:outline-none focus:border-cyan-500 cursor-pointer"
            >
              <option value="" disabled>Add Location...</option>
              {(filterOptions.locations || []).map(loc => (
                <option key={loc} value={loc}>{loc}</option>
              ))}
            </select>

            {/* Location pills */}
            {(activeFilters.locations || []).length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1.5">
                {activeFilters.locations.map(loc => (
                  <span
                    key={loc}
                    onClick={() => {
                      updateFilter("locations", activeFilters.locations.filter(l => l !== loc));
                    }}
                    className="px-2 py-0.5 bg-cyan-950/40 border border-cyan-800/60 rounded text-[9px] text-cyan-400 font-bold hover:bg-rose-950/20 hover:border-rose-900/40 hover:text-rose-400 cursor-pointer flex items-center gap-1 transition-all"
                  >
                    {loc} <span className="text-[8px]">×</span>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Work Mode Toggle Row */}
          <div className="text-[10px]">
            <label className="text-[8px] font-bold text-slate-500 uppercase block mb-1">Work Mode</label>
            <div className="flex gap-1.5">
              {["Remote", "Hybrid", "Onsite"].map(mode => {
                const isActive = activeFilters.work_modes.includes(mode);
                return (
                  <button
                    key={mode}
                    onClick={() => {
                      const next = isActive
                        ? activeFilters.work_modes.filter(m => m !== mode)
                        : [...activeFilters.work_modes, mode];
                      updateFilter("work_modes", next);
                    }}
                    className={`flex-1 py-1 rounded-lg text-[9px] font-black uppercase border transition-all ${isActive
                      ? "bg-cyan-500 text-black border-cyan-500 shadow-sm"
                      : "bg-slate-950 border-slate-850 text-slate-400 hover:bg-slate-900 hover:text-white"
                      }`}
                  >
                    {mode}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Validation Tiers Multi-select Row */}
          <div className="text-[10px] mt-1">
            <label className="text-[8px] font-bold text-slate-500 uppercase block mb-1">Quality Tiers</label>
            <div className="flex gap-1.5">
              {[
                { id: "A", label: "★★★★★ A" },
                { id: "B", label: "★★★★☆ B" },
                { id: "C", label: "★★★☆☆ C" }
              ].map(tier => {
                const isActive = activeFilters.tiers.includes(tier.id);
                return (
                  <button
                    key={tier.id}
                    onClick={() => {
                      const next = isActive
                        ? activeFilters.tiers.filter(t => t !== tier.id)
                        : [...activeFilters.tiers, tier.id];
                      updateFilter("tiers", next);
                    }}
                    className={`flex-1 py-1 rounded-lg text-[8px] font-black uppercase border transition-all ${isActive
                      ? "bg-emerald-500 text-black border-emerald-500 shadow-sm"
                      : "bg-slate-950 border-slate-850 text-slate-400 hover:bg-slate-900 hover:text-white"
                      }`}
                  >
                    {tier.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Direct sources toggle switch */}
          <label className="flex items-center gap-2 cursor-pointer mt-1">
            <input
              type="checkbox"
              checked={
                activeFilters.sources.length === 6 &&
                ["Company Careers", "Greenhouse", "Lever", "Ashby", "Workable", "SmartRecruiters"].every(s => activeFilters.sources.includes(s))
              }
              onChange={(e) => {
                const isChecked = e.target.checked;
                updateFilter("sources", isChecked ? ["Company Careers", "Greenhouse", "Lever", "Ashby", "Workable", "SmartRecruiters"] : []);
              }}
              className="rounded bg-slate-950 border-slate-850 text-cyan-500 focus:ring-cyan-500 w-3.5 h-3.5 cursor-pointer"
            />
            <span className="text-[9px] font-bold text-cyan-400 flex items-center gap-1">
              Direct Sources Only
            </span>
          </label>
        </div>

        {/* Filter Analytics result counts */}
        <div className="flex items-center justify-between px-4 py-2 bg-slate-950/40 border-b border-slate-800 text-[9px] font-black tracking-wider uppercase text-slate-400">
          <span>Collected: <span className="text-indigo-400">{validationReport.jobs_collected || 0}</span></span>
          <span>Validated: <span className="text-emerald-400">{validationReport.jobs_displayed || 0}</span></span>
          <span>Filtered: <span className="text-cyan-400">{jobs.length}</span></span>
        </div>

        {/* LIST CONTAINER */}
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {filteredJobs.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <p className="text-xs">No matching jobs found.</p>
              <p className="text-[10px] mt-1 text-slate-600">Update preferences in Profile to refresh.</p>
            </div>
          ) : (
            <>
              {/* Tier A Section */}
              {currentJobs.filter(j => j.validation_tier === "A").length > 0 && (
                <div className="space-y-2">
                  <div className="text-[10px] font-black uppercase text-emerald-400 tracking-wider mb-2 px-1 flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    Tier A: Excellent Match ({currentJobs.filter(j => j.validation_tier === "A").length})
                  </div>
                  {currentJobs.filter(j => j.validation_tier === "A").map((job) => renderJobCard(job))}
                </div>
              )}

              {/* Tier B Section */}
              {currentJobs.filter(j => j.validation_tier === "B").length > 0 && (
                <div className="space-y-2 mt-3">
                  <div className="text-[10px] font-black uppercase text-blue-400 tracking-wider mb-2 px-1 flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-blue-400"></span>
                    Tier B: Strong Match ({currentJobs.filter(j => j.validation_tier === "B").length})
                  </div>
                  {currentJobs.filter(j => j.validation_tier === "B").map((job) => renderJobCard(job))}
                </div>
              )}

              {/* Tier C Section */}
              {currentJobs.filter(j => j.validation_tier === "C").length > 0 && (
                <div className="space-y-2 mt-3 border-t border-slate-800/40 pt-3">
                  <button
                    onClick={() => setShowTierC(!showTierC)}
                    className="w-full text-left text-[10px] font-black uppercase text-slate-400 hover:text-slate-300 tracking-wider mb-2 px-1 flex items-center justify-between transition-colors focus:outline-none"
                  >
                    <span className="flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-slate-500"></span>
                      Tier C: Possible Matches ({currentJobs.filter(j => j.validation_tier === "C").length})
                    </span>
                    <span>{showTierC ? "▲ Hide" : "▶ Show"}</span>
                  </button>
                  {showTierC && currentJobs.filter(j => j.validation_tier === "C").map((job) => renderJobCard(job))}
                </div>
              )}

              {totalPages > 1 && (
                <div className="flex items-center justify-between p-2 bg-slate-950/40 border border-slate-800/80 rounded-xl my-2">
                  <button
                    onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                    disabled={currentPage === 1}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 disabled:hover:bg-slate-800 rounded-lg text-[10px] font-bold uppercase transition-colors"
                  >
                    Prev
                  </button>
                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                    disabled={currentPage === totalPages}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 disabled:hover:bg-slate-800 rounded-lg text-[10px] font-bold uppercase transition-colors"
                  >
                    Next
                  </button>
                </div>
              )}

              <div className="pt-2 pb-4">
                <button
                  onClick={handleLoadMore}
                  disabled={isLoadingMore}
                  className="w-full py-3 px-4 bg-slate-950 hover:bg-slate-800 border border-slate-800 hover:border-cyan-500/50 rounded-xl text-xs font-black tracking-wider uppercase text-cyan-400 hover:text-cyan-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2"
                >
                  {isLoadingMore ? (
                    <>
                      <svg className="animate-spin h-4 w-4 text-cyan-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Scraping Relevant Jobs (No hurry)...
                    </>
                  ) : (
                    "Show More Jobs"
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* MIDDLE PANE: JOB DETAIL PANE (6/12 width) */}
      <div className="flex-1 flex flex-col bg-slate-950 overflow-y-auto p-4 md:p-6 border-r border-slate-800">
        {selectedJob ? (
          <div className="space-y-6">

            {/* DETAILS HEADER */}
            <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl flex flex-col gap-4 shadow-xl relative overflow-hidden">
              <div className="flex justify-between items-start gap-4">
                <div>
                  <h2 className="text-xl md:text-2xl font-black text-slate-100 leading-tight">{selectedJob.title}</h2>
                  <p className="text-xs font-bold text-cyan-400 mt-2 flex flex-wrap items-center gap-2">
                    {selectedJob.company}
                    <button
                      onClick={() => handleVerifyCompany(selectedJob.company)}
                      className="px-2.5 py-0.5 bg-slate-800 hover:bg-slate-700 text-[9px] text-slate-300 rounded font-bold flex items-center gap-1 border border-slate-700 transition-colors"
                    >
                      <FaSearch className="text-[8px]" /> Verify Company <FaExternalLinkAlt className="text-[7px]" />
                    </button>
                    <span className={`px-2 py-0.5 text-[9px] rounded font-bold uppercase tracking-wide border ${(selectedJob.evaluation_mode || "Local Heuristics").toLowerCase().includes("ai")
                      ? "bg-cyan-950/40 border-cyan-800/60 text-cyan-400"
                      : "bg-amber-950/40 border-amber-800/60 text-amber-400"
                      }`}>
                      {selectedJob.evaluation_mode || "Local Heuristics"}
                    </span>
                  </p>
                </div>
                <div className={`px-4 py-2 rounded-xl border text-center ${getScoreColor(selectedJob.match_score)}`}>
                  <div className="text-[9px] text-slate-400 font-bold uppercase tracking-wider">Airohunt Score</div>
                  <div className="text-lg font-black">{selectedJob.match_score}%</div>
                </div>
              </div>

              {/* DETAILED SCORE METER BREAKDOWN */}
              <div className="grid grid-cols-4 gap-2 bg-slate-950/60 p-3 rounded-xl border border-slate-800/80 text-[10px] text-slate-300">
                <div className="text-center border-r border-slate-800">
                  <span className="text-slate-500 font-bold block uppercase tracking-wider text-[8px]">Tech Match</span>
                  <span className="font-semibold text-xs mt-0.5 block">{selectedJob.tech_match_score}%</span>
                </div>
                <div className="text-center border-r border-slate-800">
                  <span className="text-slate-500 font-bold block uppercase tracking-wider text-[8px]">Preference</span>
                  <span className="font-semibold text-xs mt-0.5 block">{selectedJob.pref_match_score}%</span>
                </div>
                <div className="text-center border-r border-slate-800">
                  <span className="text-slate-500 font-bold block uppercase tracking-wider text-[8px]">Company Trust</span>
                  <span className="font-semibold text-xs mt-0.5 block">{selectedJob.trust_score}%</span>
                </div>
                <div className="text-center">
                  <span className="text-slate-500 font-bold block uppercase tracking-wider text-[8px]">Opportunity</span>
                  <span className="font-semibold text-xs mt-0.5 block">{selectedJob.opportunity_score}%</span>
                </div>
              </div>

              {/* ACTION ROW */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Status:</span>
                  <select
                    value={selectedJob.status || "Matched"}
                    onChange={(e) => updateQueueStatus(selectedJob.id, e.target.value)}
                    className="bg-slate-800 border border-slate-700 rounded-lg text-xs font-bold text-white px-3 py-1.5 focus:outline-none focus:border-cyan-500 cursor-pointer"
                  >
                    <option value="Matched">Matched</option>
                    <option value="Prepared">Prepared</option>
                    <option value="Applied">Applied</option>
                    <option value="Interviewing">Interviewing</option>
                    <option value="Ghosted">Ghosted</option>
                    <option value="Rejected">Rejected</option>
                    <option value="Offered">Offered</option>
                  </select>
                </div>

                <div className="flex gap-2">
                  {(selectedJob.tailored_resume || selectedJob.status === "Prepared") && (
                    <button
                      onClick={() => setShowResumeModal(true)}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-cyan-800/40 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all"
                    >
                      <FaFileAlt /> View Resume & Autofill
                    </button>
                  )}

                  <a
                    href={selectedJob.url}
                    target="_blank"
                    rel="noreferrer"
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all"
                  >
                    <FaExternalLinkAlt className="text-[10px]" /> Apply on Company Site
                  </a>

                  <button
                    onClick={() => handleApply(selectedJob.id)}
                    className="px-5 py-2 bg-gradient-to-r from-cyan-500 to-emerald-400 hover:from-cyan-400 hover:to-emerald-300 text-black font-black rounded-xl text-xs flex items-center gap-1.5 shadow-md shadow-cyan-500/10 hover:scale-105 transition-all"
                  >
                    <FaCheckCircle /> Apply & Tailor
                  </button>
                </div>
              </div>
            </div>

            {/* STRICT JOB VALIDATION REPORT & BADGE DETAILS */}
            <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl space-y-4 shadow-xl">
              <div className="flex justify-between items-center border-b border-slate-800/60 pb-3">
                <h3 className="text-xs font-black uppercase text-slate-400 tracking-wider flex items-center gap-1.5">
                  <FaShieldAlt className="text-cyan-400" /> Strict Validation Scorecard
                </h3>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-500 font-bold">Confidence:</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-black border ${selectedJob.validation_confidence >= 80
                    ? 'bg-emerald-950/40 border-emerald-800/40 text-emerald-400'
                    : selectedJob.validation_confidence >= 50
                      ? 'bg-cyan-950/40 border-cyan-800/40 text-cyan-400'
                      : 'bg-rose-950/40 border-rose-800/40 text-rose-400'
                    }`}>
                    {selectedJob.validation_confidence || 0}%
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                {/* Score & Tier Badge */}
                <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800 flex flex-col justify-between items-center text-center">
                  <div>
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Validation Grade</span>
                    <span className={`text-sm font-black mt-1.5 block ${selectedJob.validation_tier === 'A' ? 'text-emerald-400' :
                      selectedJob.validation_tier === 'B' ? 'text-blue-400' :
                        selectedJob.validation_tier === 'C' ? 'text-amber-400' : 'text-slate-400'
                      }`}>
                      {getTierStars(selectedJob.validation_tier)} (Tier {selectedJob.validation_tier || 'B'})
                    </span>
                  </div>
                  <div className="mt-3 text-[10px] text-slate-400">
                    Validation Score: <span className="font-bold text-white text-xs">{selectedJob.validation_score || 0}/100</span>
                  </div>
                </div>

                {/* Checklist Compatibility & Warnings */}
                <div className="space-y-3">
                  <div>
                    <span className="text-slate-500 font-bold block uppercase tracking-wider text-[9px] mb-1.5">Compliance Checklist</span>
                    <div className="space-y-1">
                      {(!selectedJob.validation_reasons || selectedJob.validation_reasons.length === 0) ? (
                        <span className="text-slate-500 italic block">No rules evaluated.</span>
                      ) : (
                        selectedJob.validation_reasons.map((reason, idx) => (
                          <div key={idx} className="flex items-center gap-1.5 text-slate-300 font-semibold">
                            <span className="text-emerald-400 text-xs flex-shrink-0">✓</span>
                            <span>{reason}</span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {selectedJob.validation_warnings && selectedJob.validation_warnings.length > 0 && (
                    <div>
                      <span className="text-amber-500 font-bold block uppercase tracking-wider text-[9px] mb-1.5">Deductions & Warnings</span>
                      <div className="space-y-1">
                        {selectedJob.validation_warnings.map((warning, idx) => (
                          <div key={idx} className="flex items-center gap-1.5 text-slate-300 font-semibold">
                            <span className="text-amber-500 text-xs flex-shrink-0">⚠</span>
                            <span>{warning}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* COMPANY RESEARCH ASSISTANT */}
            <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl space-y-4 shadow-xl">
              <div className="flex justify-between items-center border-b border-slate-800/60 pb-3">
                <h3 className="text-xs font-black uppercase text-slate-400 tracking-wider flex items-center gap-1.5">
                  <FaRocket className="text-cyan-400" /> Company Research Assistant
                </h3>
                <div className="flex items-center gap-1">
                  <span className="text-[10px] text-slate-500 font-bold">Trust Rating:</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-black border ${selectedJob.trust_rating === 'A+' || selectedJob.trust_rating === 'A'
                    ? 'bg-emerald-950/40 border-emerald-800/40 text-emerald-400'
                    : selectedJob.trust_rating === 'B'
                      ? 'bg-cyan-950/40 border-cyan-800/40 text-cyan-400'
                      : selectedJob.trust_rating === 'C'
                        ? 'bg-amber-950/40 border-amber-800/40 text-amber-400'
                        : 'bg-rose-950/40 border-rose-800/40 text-rose-400'
                    }`}>
                    {selectedJob.trust_rating || 'B'}
                  </span>
                </div>
              </div>

              <div className="space-y-3 text-xs leading-relaxed">
                <div>
                  <span className="text-slate-500 font-bold block uppercase tracking-wider text-[9px]">Company Summary</span>
                  <p className="text-slate-300 mt-1">{selectedJob.company_summary || `${selectedJob.company} is an active technology company hiring in the region.`}</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <span className="text-slate-500 font-bold block uppercase tracking-wider text-[9px] mb-1.5">Tech Stack</span>
                    <div className="flex flex-wrap gap-1.5">
                      {(selectedJob.tech_stack || []).length === 0 ? (
                        <span className="text-slate-500 italic">No technology tags found.</span>
                      ) : (
                        (selectedJob.tech_stack || []).map((tech, idx) => (
                          <span key={idx} className="px-2 py-0.5 bg-slate-950 border border-slate-800 rounded text-[10px] text-slate-400 font-semibold">
                            {tech}
                          </span>
                        ))
                      )}
                    </div>
                  </div>

                  <div>
                    <span className="text-slate-500 font-bold block uppercase tracking-wider text-[9px] mb-1.5">Hiring Signals</span>
                    <div className="space-y-1">
                      {(selectedJob.hiring_signals || []).length === 0 ? (
                        <span className="text-slate-300 font-semibold">Standard Hiring Reviews</span>
                      ) : (
                        (selectedJob.hiring_signals || []).map((signal, idx) => (
                          <div key={idx} className="flex items-center gap-1.5 text-slate-300 font-semibold">
                            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 flex-shrink-0"></span>
                            <span>{signal}</span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* EXPLAINABLE AI RECOMMENDATIONS (Why recommended / Warnings) */}
            <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl space-y-4 shadow-xl">
              <div>
                <h3 className="text-xs font-black uppercase text-slate-400 tracking-wider flex items-center gap-1.5">
                  <FaShieldAlt className="text-cyan-500" /> Explainable Match Analysis
                </h3>
                <p className="text-xs text-slate-300 mt-2 leading-relaxed italic bg-slate-950/40 p-3 rounded-lg border border-slate-800">
                  "{selectedJob.ai_recommendation}"
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-800/60 text-xs">
                {/* Pros */}
                <div className="space-y-2">
                  <h4 className="text-[10px] font-black uppercase tracking-wider text-emerald-400">Why recommended</h4>
                  <div className="space-y-1.5">
                    {selectedJob.recommendation_pros.length === 0 ? (
                      <span className="text-slate-500 italic">No specific positive factors.</span>
                    ) : (
                      selectedJob.recommendation_pros.map((pro, index) => (
                        <div key={index} className="flex items-center gap-1.5 text-slate-300 font-semibold">
                          <FaCheckCircle className="text-emerald-400 text-xs flex-shrink-0" />
                          <span>{pro}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Warnings (Cons) */}
                <div className="space-y-2">
                  <h4 className="text-[10px] font-black uppercase tracking-wider text-amber-500">Warnings / Exclusions</h4>
                  <div className="space-y-1.5">
                    {selectedJob.recommendation_cons.length === 0 ? (
                      <div className="flex items-center gap-1.5 text-slate-500">
                        <FaCheckCircle className="text-emerald-500/50 text-xs flex-shrink-0" />
                        <span className="italic">No negative red flags.</span>
                      </div>
                    ) : (
                      selectedJob.recommendation_cons.map((con, index) => (
                        <div key={index} className="flex items-center gap-1.5 text-slate-300 font-semibold">
                          <FaExclamationTriangle className="text-amber-500 text-xs flex-shrink-0" />
                          <span>{con}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* DESCRIPTION */}
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-slate-200">Job Description</h3>
              <p className="text-slate-300 text-xs md:text-sm leading-relaxed whitespace-pre-line bg-slate-900/30 p-5 rounded-2xl border border-slate-900">
                {selectedJob.description}
              </p>
            </div>

            {/* SKILLS */}
            <div className="space-y-3">
              <h3 className="text-xs font-black uppercase text-slate-400 tracking-wider">Required Skills Check</h3>
              <div className="flex flex-wrap gap-1.5">
                {selectedJob.skills_required.map((skill, index) => {
                  const profile = useStore.getState().profile;
                  const isMatched = profile.skills.some(s => s.toLowerCase() === skill.toLowerCase());
                  return (
                    <span
                      key={index}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold border flex items-center gap-1 ${isMatched
                        ? "bg-emerald-950/40 border-emerald-500/30 text-emerald-400"
                        : "bg-slate-900 border-slate-800 text-slate-500"
                        }`}
                    >
                      {isMatched ? <FaCheck className="text-[9px]" /> : null} {skill}
                    </span>
                  );
                })}
              </div>
            </div>

          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-500 text-xs">
            Select a job from the pool to view details.
          </div>
        )}
      </div>

      {/* RIGHT PANE: STARTUP RADAR (3/12 width) */}
      <div className="w-full lg:w-3/12 border-l border-slate-800 flex flex-col bg-slate-900/40">

        {/* PANEL TITLE */}
        <div className="p-4 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between">
          <h2 className="font-bold text-xs text-slate-300 tracking-wider uppercase flex items-center gap-1.5">
            <FaRocket className="text-emerald-400 text-xs" /> Startup Listing
          </h2>
          <span className="text-[9px] bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded-full text-emerald-400 font-black tracking-wider uppercase">
            Hiring Local
          </span>
        </div>

        {/* RADAR CONTAINER */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {startups.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <p className="text-xs">No active startups tracked.</p>
              <p className="text-[10px] mt-1 text-slate-600">Startups sync when profile region is set.</p>
            </div>
          ) : (
            <>
              {startups.slice((currentStartupPage - 1) * startupsPerPage, currentStartupPage * startupsPerPage).map((company, index) => (
                <div
                  key={index}
                  className="p-3 bg-slate-950/50 border border-slate-800 rounded-xl hover:border-slate-700 transition-all flex flex-col gap-2.5 relative overflow-hidden"
                >
                  <div className="flex justify-between items-start gap-1">
                    <div>
                      <h4 className="font-black text-slate-200 text-xs leading-tight">{company.company}</h4>
                      <p className="text-[10px] text-cyan-400 font-bold mt-1">{company.title}</p>
                    </div>
                    <div className="text-[9px] font-black text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded">
                      {company.relevance}% Rel
                    </div>
                  </div>

                  <div className="space-y-1 text-[10px] text-slate-400">
                    <div className="flex items-center gap-1 truncate"><FaMapMarkerAlt className="text-slate-500" /> {company.location}</div>
                    <div className="flex items-center gap-1 text-emerald-400 font-semibold"><FaDollarSign /> {company.salary}</div>
                  </div>

                  <div className="flex flex-wrap gap-1 mt-1">
                    {(company.skills || []).slice(0, 3).map((skill, sIdx) => (
                      <span key={sIdx} className="text-[8px] bg-slate-900 border border-slate-800 px-1.5 py-0.5 rounded text-slate-400 font-bold">
                        {skill}
                      </span>
                    ))}
                  </div>

                  <a
                    href={company.url}
                    target="_blank"
                    rel="noreferrer"
                    className="w-full py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-[9px] font-black text-center uppercase tracking-widest text-slate-300 hover:text-white mt-1 transition-colors flex items-center justify-center gap-1"
                  >
                    Apply Link <FaExternalLinkAlt className="text-[7px]" />
                  </a>
                </div>
              ))}

              {totalStartupPages > 1 && (
                <div className="flex items-center justify-between p-2 bg-slate-950/40 border border-slate-800/80 rounded-xl my-2">
                  <button
                    onClick={() => setCurrentStartupPage(prev => Math.max(prev - 1, 1))}
                    disabled={currentStartupPage === 1}
                    className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 disabled:hover:bg-slate-800 rounded-lg text-[9px] font-bold uppercase transition-colors"
                  >
                    Prev
                  </button>
                  <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider">
                    Page {currentStartupPage} of {totalStartupPages}
                  </span>
                  <button
                    onClick={() => setCurrentStartupPage(prev => Math.min(prev + 1, totalStartupPages))}
                    disabled={currentStartupPage === totalStartupPages}
                    className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 disabled:hover:bg-slate-800 rounded-lg text-[9px] font-bold uppercase transition-colors"
                  >
                    Next
                  </button>
                </div>
              )}

              <div className="pt-2 pb-4">
                <button
                  onClick={handleLoadMoreStartups}
                  disabled={isLoadingMoreStartups}
                  className="w-full py-2.5 px-3 bg-slate-950 hover:bg-slate-800 border border-slate-800 hover:border-emerald-500/50 rounded-xl text-[10px] font-black tracking-wider uppercase text-emerald-400 hover:text-emerald-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-1.5"
                >
                  {isLoadingMoreStartups ? (
                    <>
                      <svg className="animate-spin h-3.5 w-3.5 text-emerald-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Discovering...
                    </>
                  ) : (
                    <>
                      <FaRocket /> Discover More Startups
                    </>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      </div>

      {/* ATS PREPARATION & APPLICATION HELPER MODAL */}
      {showResumeModal && selectedJob && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-6xl h-[88vh] flex flex-col shadow-2xl overflow-hidden">

            {/* MODAL HEADER */}
            <div className="px-6 py-4 bg-slate-900 border-b border-slate-800 flex items-center justify-between flex-shrink-0">
              <div>
                <h2 className="text-lg font-black text-white flex items-center gap-2">
                  <FaShieldAlt className="text-cyan-400" /> ATS Preparation & Application Helper
                </h2>
                <p className="text-xs text-slate-400 font-semibold mt-0.5">{selectedJob.title} — {selectedJob.company}</p>
              </div>
              <div className="flex gap-2">
                <a
                  href={selectedJob.url}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-cyan-400 hover:from-cyan-400 hover:to-cyan-300 text-black rounded-xl text-xs font-black flex items-center gap-1.5 transition-all"
                >
                  Open Application Page <FaExternalLinkAlt className="text-[8px]" />
                </a>
                <button
                  onClick={async () => {
                    await updateQueueStatus(selectedJob.id, "Applied");
                    setShowResumeModal(false);
                    Swal.fire({
                      toast: true,
                      position: 'top-end',
                      icon: 'success',
                      title: 'Marked as Applied!',
                      showConfirmButton: false,
                      timer: 2000,
                      background: "#0f172a",
                      color: "#fff"
                    });
                  }}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-black font-black rounded-xl text-xs flex items-center gap-1.5 transition-all"
                >
                  <FaCheck /> Mark as Submitted
                </button>
                <button
                  onClick={() => setShowResumeModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-xl text-xs font-bold transition-all"
                >
                  Close
                </button>
              </div>
            </div>

            {/* MODAL COLUMNS CONTAINER */}
            <div className="flex-1 flex flex-col md:flex-row overflow-hidden">

              {/* LEFT COLUMN: FILL ASSISTANCE & AUTOFILL SCRIPT */}
              <div className="flex-1 border-r border-slate-800 flex flex-col overflow-hidden bg-slate-950/20">
                <div className="px-4 py-2 bg-slate-900/60 border-b border-slate-800 text-[10px] font-black uppercase text-cyan-400 tracking-wider flex justify-between items-center">
                  <span>Form Fill Assistance</span>
                  <span className="text-[9px] bg-slate-800 border border-slate-700 px-2 py-0.5 rounded text-slate-300">
                    Platform: {selectedJob.autofill_data?.platform || "Generic"} ({selectedJob.autofill_data?.automation_support || "40%"})
                  </span>
                </div>

                <div className="flex-1 p-6 overflow-y-auto space-y-5 text-xs">
                  {/* Standard Profile Fields */}
                  <div className="space-y-2">
                    <h4 className="text-[10px] font-black uppercase text-slate-500 tracking-wider">Standard Mapped Fields</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {selectedJob.autofill_data?.mapped_fields &&
                        Object.entries(selectedJob.autofill_data.mapped_fields).map(([label, val]) => (
                          <div key={label} className="p-2 bg-slate-900 border border-slate-800 rounded-xl flex justify-between items-center min-w-0">
                            <div className="min-w-0">
                              <span className="text-[9px] text-slate-500 font-bold block uppercase">{label}</span>
                              <span className="text-slate-300 font-semibold truncate block mt-0.5">{val}</span>
                            </div>
                            <button
                              onClick={() => copyToClipboard(val)}
                              className="p-1 text-cyan-500 hover:text-cyan-300 transition-colors flex-shrink-0"
                              title="Copy Field"
                            >
                              <FaCopy className="text-[11px]" />
                            </button>
                          </div>
                        ))}
                    </div>
                  </div>

                  {/* Required Questions Detector */}
                  {selectedJob.autofill_data?.custom_questions && selectedJob.autofill_data.custom_questions.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-[10px] font-black uppercase text-amber-500 tracking-wider">Detected Form Questions</h4>
                      <div className="space-y-2">
                        {selectedJob.autofill_data.custom_questions.map((q) => (
                          <div key={q.id} className="p-2.5 bg-amber-950/10 border border-amber-900/30 rounded-xl flex justify-between items-start gap-2">
                            <div>
                              <span className="text-[10px] text-amber-400 font-bold block">{q.label}</span>
                              <span className="text-[9px] text-slate-500 italic block mt-0.5">{q.placeholder}</span>
                            </div>
                            <button
                              onClick={() => copyToClipboard(q.label)}
                              className="text-[9px] bg-slate-800 text-slate-300 px-2 py-1 rounded font-bold hover:bg-slate-700 hover:text-white transition-all flex-shrink-0"
                            >
                              Copy
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Console Auto-Fill Script */}
                  {selectedJob.autofill_data?.autofill_script && (
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <h4 className="text-[10px] font-black uppercase text-cyan-400 tracking-wider">Console Auto-Fill Script</h4>
                        <button
                          onClick={() => copyScriptToClipboard(selectedJob.autofill_data.autofill_script)}
                          className="px-2 py-1 bg-cyan-950 border border-cyan-800 text-cyan-400 rounded text-[9px] font-black uppercase hover:bg-cyan-900 transition-all"
                        >
                          {copiedScript ? "Copied Script!" : "Copy Full Script"}
                        </button>
                      </div>
                      <p className="text-[9px] text-slate-500 leading-normal">
                        To auto-fill this application form: Open the job page, press <kbd className="bg-slate-900 px-1 py-0.5 rounded border border-slate-800 text-slate-400">F12</kbd> (or right click -&gt; Inspect), go to the **Console** tab, paste the copied script, and press **Enter**.
                      </p>
                      <pre className="p-3 bg-slate-950 border border-slate-800 rounded-xl text-[9px] font-mono text-slate-400 overflow-x-auto max-h-[140px] leading-relaxed">
                        {selectedJob.autofill_data.autofill_script}
                      </pre>
                    </div>
                  )}

                </div>
              </div>

              {/* RIGHT COLUMN: TAILORED ATS RESUME */}
              <div className="flex-1 flex flex-col overflow-hidden bg-slate-950/50">
                <div className="px-4 py-2 bg-slate-900/60 border-b border-slate-800 text-[10px] font-black uppercase text-cyan-400 tracking-wider flex justify-between items-center">
                  <span>Tailored Copy (ATS Optimized Resume)</span>
                  <button
                    onClick={() => copyToClipboard(selectedJob.tailored_resume)}
                    className="text-[9px] text-cyan-400 hover:text-cyan-300 font-black uppercase tracking-wider flex items-center gap-1"
                  >
                    {copied ? <FaCheck className="text-emerald-400" /> : <FaCopy />} {copied ? "Copied!" : "Copy Resume"}
                  </button>
                </div>
                <div className="flex-1 p-6 overflow-y-auto text-slate-200 text-xs font-mono whitespace-pre-wrap leading-relaxed bg-slate-950/80">
                  {selectedJob.tailored_resume || "No tailored resume prepared."}
                </div>
              </div>

            </div>

          </div>
        </div>
      )}

      {/* CAREER METRICS & ACTIVITY AUDIT LOGS MODAL */}
      {showMetricsModal && metrics && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-3xl h-[75vh] flex flex-col shadow-2xl overflow-hidden">

            {/* HEADER */}
            <div className="px-6 py-4 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-black text-white flex items-center gap-2">
                  <FaShieldAlt className="text-emerald-400" /> Career Metrics & Safety Audit Log
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">Historical tracking of automated actions and response rates.</p>
              </div>
              <button
                onClick={() => setShowMetricsModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-xl text-xs font-bold transition-all"
              >
                Close
              </button>
            </div>

            {/* CONTENT */}
            <div className="flex-1 p-6 overflow-y-auto space-y-6">

              {/* METRICS GRID */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl text-center">
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Applications Submitted</span>
                  <span className="text-2xl font-black text-emerald-400 mt-1 block">{metrics.total_submitted || 0}</span>
                </div>
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl text-center">
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Interview Response Rate</span>
                  <span className="text-2xl font-black text-cyan-400 mt-1 block">{metrics.interview_rate || 0.0}%</span>
                </div>
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl text-center col-span-2 md:col-span-1">
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Best Performing Source</span>
                  <span className="text-sm font-black text-slate-200 mt-2.5 block truncate px-2">{metrics.best_source || "N/A"}</span>
                </div>
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl text-center col-span-2">
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Best Performing Resume Version</span>
                  <span className="text-sm font-black text-cyan-400 mt-2 block truncate">{metrics.best_resume || "N/A"}</span>
                </div>
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl text-center col-span-2 md:col-span-1">
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Offer Success Rate</span>
                  <span className="text-2xl font-black text-indigo-400 mt-1 block">{metrics.offer_rate || 0.0}%</span>
                </div>
              </div>

              {/* AUDIT TRAILS */}
              <div className="space-y-3">
                <h3 className="text-xs font-black uppercase text-slate-400 tracking-wider">Safety Audit Trail</h3>
                <div className="bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden max-h-[220px] overflow-y-auto divide-y divide-slate-800/60">
                  {(!metrics.audit_logs || metrics.audit_logs.length === 0) ? (
                    <div className="p-6 text-center text-slate-500 italic text-xs">
                      No automated events logged yet. Tailor a resume to register activity.
                    </div>
                  ) : (
                    [...metrics.audit_logs].reverse().map((log, idx) => (
                      <div key={idx} className="p-3 text-[11px] leading-relaxed flex flex-col sm:flex-row justify-between gap-1">
                        <div>
                          <span className="text-slate-300 font-semibold block sm:inline">{log.action}</span>
                          <span className="text-slate-500 text-[10px] ml-0 sm:ml-2">({log.title} @ {log.company})</span>
                        </div>
                        <span className="text-slate-500 text-[10px] font-mono flex-shrink-0 self-start sm:self-center">
                          {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>

            </div>

          </div>
        </div>
      )}
      {/* AIROHUNT PERFORMANCE & STRICT VALIDATION REPORT MODAL */}
      {showValidationModal && validationReport && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-4xl h-[80vh] flex flex-col shadow-2xl overflow-hidden">

            {/* HEADER */}
            <div className="px-6 py-4 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-black text-white flex items-center gap-2">
                  <FaShieldAlt className="text-indigo-400" /> Airohunt Quality Validation Report
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">Performance analytics of the strict filter engine.</p>
              </div>
              <button
                onClick={() => setShowValidationModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-xl text-xs font-bold transition-all"
              >
                Close
              </button>
            </div>

            {/* CONTENT */}
            <div className="flex-1 p-6 overflow-y-auto space-y-6">

              {/* STATS COUNTERS */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl text-center">
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Total Scraped</span>
                  <span className="text-2xl font-black text-indigo-400 mt-1 block">{validationReport.jobs_collected || 0}</span>
                </div>
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl text-center">
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Displayed (A/B/C)</span>
                  <span className="text-2xl font-black text-emerald-400 mt-1 block">{validationReport.jobs_displayed || 0}</span>
                </div>
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl text-center">
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Hard Rejected (D)</span>
                  <span className="text-2xl font-black text-rose-500 mt-1 block">{validationReport.jobs_rejected || 0}</span>
                </div>
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl text-center">
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Duplicates Removed</span>
                  <span className="text-2xl font-black text-blue-400 mt-1 block">{validationReport.duplicates_removed || 0}</span>
                </div>
              </div>

              {/* DETAILED REJECTIONS BREAKDOWN */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                {/* BLOCKED CATEGORIES */}
                <div className="p-5 bg-slate-950 border border-slate-800 rounded-2xl space-y-3">
                  <h3 className="text-xs font-black uppercase text-slate-400 tracking-wider">Blocked Listings Categories</h3>
                  <div className="space-y-2.5 text-xs">
                    <div className="flex justify-between items-center py-1 border-b border-slate-900">
                      <span className="text-slate-400">Scams Blocked</span>
                      <span className="font-bold text-rose-400">{validationReport.scams_blocked || 0}</span>
                    </div>
                    <div className="flex justify-between items-center py-1 border-b border-slate-900">
                      <span className="text-slate-400">Training/Course Sellers Blocked</span>
                      <span className="font-bold text-rose-400">{validationReport.training_institutes_blocked || 0}</span>
                    </div>
                    <div className="flex justify-between items-center py-1">
                      <span className="text-slate-400">Experience Threshold Rejected</span>
                      <span className="font-bold text-rose-400">{validationReport.experience_rejected || 0}</span>
                    </div>
                  </div>
                </div>

                {/* TOP FAILURE REASONS LIST */}
                <div className="p-5 bg-slate-950 border border-slate-800 rounded-2xl space-y-3">
                  <h3 className="text-xs font-black uppercase text-slate-400 tracking-wider">Top Filter Violations</h3>
                  <div className="space-y-2 text-xs">
                    {(!validationReport.top_failure_reasons || validationReport.top_failure_reasons.length === 0) ? (
                      <div className="text-slate-500 italic text-center py-4">No filter violations recorded.</div>
                    ) : (
                      validationReport.top_failure_reasons.map((item, idx) => (
                        <div key={idx} className="flex justify-between items-center">
                          <span className="text-slate-400 flex items-center gap-1">
                            <span className="text-rose-500">●</span> {item.reason}
                          </span>
                          <span className="font-bold text-slate-200">{item.count}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

              </div>

              {/* HISTORICAL LOG */}
              <div className="space-y-3">
                <h3 className="text-xs font-black uppercase text-slate-400 tracking-wider">Historical Experiment Runs</h3>
                <div className="bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden overflow-x-auto">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-900 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-800 text-[9px]">
                        <th className="p-3">Timestamp</th>
                        <th className="p-3">Scraped</th>
                        <th className="p-3">Kept</th>
                        <th className="p-3">Tier A</th>
                        <th className="p-3">Tier B</th>
                        <th className="p-3">Tier C</th>
                        <th className="p-3">Rejected (D)</th>
                        <th className="p-3">Dups</th>
                        <th className="p-3">Scams</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-900">
                      {(!validationReport.history || validationReport.history.length === 0) ? (
                        <tr>
                          <td colSpan="9" className="p-6 text-center text-slate-500 italic">No runs recorded yet. Start a sync or scrape.</td>
                        </tr>
                      ) : (
                        [...validationReport.history].reverse().map((run, idx) => (
                          <tr key={idx} className="hover:bg-slate-900/40 text-slate-300 font-medium">
                            <td className="p-3 text-[10px] text-slate-400 font-mono">
                              {new Date(run.timestamp).toLocaleDateString()} {new Date(run.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </td>
                            <td className="p-3">{run.collected}</td>
                            <td className="p-3 text-emerald-400 font-semibold">{run.displayed}</td>
                            <td className="p-3 text-emerald-500">{run.tier_a}</td>
                            <td className="p-3 text-blue-400">{run.tier_b}</td>
                            <td className="p-3 text-amber-500">{run.tier_c}</td>
                            <td className="p-3 text-rose-500">{run.tier_d}</td>
                            <td className="p-3">{run.duplicates_removed}</td>
                            <td className="p-3 text-rose-400">{run.scams_blocked}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>

          </div>
        </div>
      )}

    </div>
  );
};

export default Dashboard;
