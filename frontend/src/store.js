import { create } from "zustand";
import {
    addEdge,
    applyNodeChanges,
    applyEdgeChanges,
    MarkerType,
} from 'reactflow';

const API_BASE = "http://127.0.0.1:8000/api";

export const useStore = create((set, get) => ({
    // Navigation & Global Loading
    activeTab: "dashboard", // dashboard, canvas, profile, settings
    isLoading: false,
    isLoadingMore: false,
    errorMessage: null,
    
    // User Profile Settings
    profile: {
        name: "",
        email: "",
        phone: "",
        location: "",
        target_roles: [],
        skills: [],
        salary_expectation: 0,
        base_resume: "",
        experience_level: "Fresher",
        preferred_work_mode: "Remote",
        region: "Kerala",
        ai_instructions: "",
        preferred_company_types: [],
        excluded_company_types: [],
        global_rules: "",
        temporary_search_rules: "",
    },
    
    // Strict Validation Report State
    validationReport: {
        jobs_collected: 0,
        jobs_rejected: 0,
        jobs_displayed: 0,
        duplicates_removed: 0,
        scams_blocked: 0,
        training_institutes_blocked: 0,
        experience_rejected: 0,
        rejection_categories: {},
        top_failure_reasons: []
    },
    
    // AI Settings State
    settings: {
        active_provider: "openai",
        openai_api_key: "",
        groq_api_key: "",
        gemini_api_key: "",
        ollama_url: "http://localhost:11434",
        source_adzuna: true,
        source_jooble: true,
        source_manual_import: false,
        source_company_careers: true,
    },
    
    // Jobs Pool State
    jobs: [],
    
    // Startup Radar State
    startups: [],
    isLoadingMoreStartups: false,

    // Smart Dynamic Filters State
    activeFilters: {
        locations: [],
        work_modes: [],
        company_types: [],
        experience_levels: [],
        tiers: ["A", "B"],
        sources: [],
        min_salary: null,
        posted_within_days: null,
        fresher_compatibility: "All"
    },
    filterOptions: {
        locations: [],
        company_types: [],
        experience_levels: [],
        sources: []
    },

    // Resume Version Profiles State
    resumes: {},

    // Application Queue State
    queue: { applications: {}, audit_logs: [] },

    // Career Memory metrics
    metrics: { total_submitted: 0, interview_rate: 0.0, offer_rate: 0.0, best_source: "N/A", best_resume: "N/A", audit_logs: [] },

    // React Flow Canvas States
    nodes: [],
    edges: [],
    nodeIDs: {},

    // Setters
    setActiveTab: (tab) => set({ activeTab: tab }),
    setLoading: (loading) => set({ isLoading: loading }),

    // React Flow Actions
    getNodeID: (type) => {
        const newIDs = { ...get().nodeIDs };
        if (newIDs[type] === undefined) {
            newIDs[type] = 0;
        }
        newIDs[type] += 1;
        set({ nodeIDs: newIDs });
        return `${type}-${newIDs[type]}`;
    },
    
    addNode: (node) => {
        set({
            nodes: [...get().nodes, node]
        });
        get().savePipeline();
    },
    
    onNodesChange: (changes) => {
        set({
            nodes: applyNodeChanges(changes, get().nodes),
        });
    },
    
    onEdgesChange: (changes) => {
        set({
            edges: applyEdgeChanges(changes, get().edges),
        });
    },
    
    onConnect: (connection) => {
        set({
            edges: addEdge(
                {
                    ...connection, 
                    type: 'smoothstep', 
                    animated: true, 
                    markerEnd: { type: MarkerType.Arrow, height: 20, width: 20, color: "#06b6d4" },
                    style: { stroke: "#06b6d4", strokeWidth: 2 }
                }, 
                get().edges
            ),
        });
        get().savePipeline();
    },
    
    updateNodeField: (nodeId, fieldName, fieldValue) => {
        set({
            nodes: get().nodes.map((node) => {
                if (node.id === nodeId) {
                    node.data = { ...node.data, [fieldName]: fieldValue };
                }
                return node;
            }),
        });
        get().savePipeline();
    },

    setNodesAndEdges: (nodes, edges) => {
        set({ nodes: nodes || [], edges: edges || [] });
    },

    // ─────────────── API ACTIONS ───────────────

    // Fetch User Profile from Backend
    fetchProfile: async () => {
        set({ isLoading: true });
        try {
            const res = await fetch(`${API_BASE}/profile`);
            if (res.ok) {
                const data = await res.json();
                set({ profile: data });
            }
        } catch (error) {
            console.error("Error fetching profile:", error);
        } finally {
            set({ isLoading: false });
        }
    },

    // Save User Profile Settings
    saveProfile: async (profileData) => {
        set({ isLoading: true });
        try {
            const res = await fetch(`${API_BASE}/profile/save`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(profileData),
            });
            if (res.ok) {
                const data = await res.json();
                set({ profile: data.profile });
                get().fetchJobs();
                get().fetchStartups();
            }
        } catch (error) {
            console.error("Error saving profile:", error);
        } finally {
            set({ isLoading: false });
        }
    },

    // Upload Resume PDF / Doc
    uploadResume: async (file) => {
        set({ isLoading: true, errorMessage: null });
        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch(`${API_BASE}/profile/upload-resume`, {
                method: "POST",
                body: formData,
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Upload failed");
            }
            const data = await res.json();
            set({ profile: data.profile });
            get().fetchJobs();
            get().fetchStartups();
            return data.message;
        } catch (error) {
            console.error("Error uploading resume:", error);
            set({ errorMessage: error.message });
            throw error;
        } finally {
            set({ isLoading: false });
        }
    },

    // Fetch Matched Jobs list (respects active filters)
    fetchJobs: async () => {
        await get().applyFilters();
        await get().fetchValidationReport();
    },

    // Trigger LLM to scrape/discover more jobs
    scrapeMoreJobs: async () => {
        set({ isLoadingMore: true });
        try {
            const res = await fetch(`${API_BASE}/jobs/scrape-more`, {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            });
            if (res.ok) {
                const data = await res.json();
                set({ jobs: data });
                get().fetchValidationReport();
                return true;
            }
            return false;
        } catch (error) {
            console.error("Error scraping more jobs:", error);
            return false;
        } finally {
            set({ isLoadingMore: false });
        }
    },

    // Update Job Tracking Status (Kanban)
    updateJobStatus: async (jobId, newStatus) => {
        try {
            const res = await fetch(`${API_BASE}/jobs/update-status`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ job_id: jobId, status: newStatus }),
            });
            if (res.ok) {
                set({
                    jobs: get().jobs.map((job) => 
                        job.id === jobId ? { ...job, status: newStatus } : job
                    )
                });
            }
        } catch (error) {
            console.error("Error updating job status:", error);
        }
    },

    // Trigger Job Application & Resume Tailoring
    applyJob: async (jobId) => {
        set({ isLoading: true });
        try {
            const res = await fetch(`${API_BASE}/jobs/apply`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ job_id: jobId }),
            });
            if (res.ok) {
                const data = await res.json();
                set({
                    jobs: get().jobs.map((job) => 
                        job.id === jobId 
                            ? { ...job, status: data.status || "Prepared", tailored_resume: data.tailored_resume, match_score: data.match_score, autofill_data: data.autofill_data } 
                            : job
                    )
                });
                get().fetchMetrics();
                return data;
            }
        } catch (error) {
            console.error("Error applying to job:", error);
        } finally {
            set({ isLoading: false });
        }
    },

    // Save Pipeline Workflow Canvas Layout
    savePipeline: async () => {
        const payload = {
            nodes: get().nodes,
            edges: get().edges,
        };
        try {
            await fetch(`${API_BASE}/pipeline/save`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
        } catch (error) {
            console.error("Error saving pipeline layout:", error);
        }
    },

    // Load Pipeline Workflow Canvas Layout
    loadPipeline: async () => {
        try {
            const res = await fetch(`${API_BASE}/pipeline/load`);
            if (res.ok) {
                const data = await res.json();
                set({ 
                    nodes: data.nodes || [], 
                    edges: data.edges || [] 
                });
            }
        } catch (error) {
            console.error("Error loading pipeline layout:", error);
        }
    },

    // Fetch AI settings
    fetchSettings: async () => {
        try {
            const res = await fetch(`${API_BASE}/settings`);
            if (res.ok) {
                const data = await res.json();
                set({ settings: data });
            }
        } catch (error) {
            console.error("Error fetching settings:", error);
        }
    },

    // Save AI settings
    saveSettings: async (settingsData) => {
        set({ isLoading: true });
        try {
            const res = await fetch(`${API_BASE}/settings/save`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(settingsData),
            });
            if (res.ok) {
                const data = await res.json();
                set({ settings: data.settings });
                get().fetchJobs(); // Re-trigger search with new engines / toggles
            }
        } catch (error) {
            console.error("Error saving settings:", error);
        } finally {
            set({ isLoading: false });
        }
    },

    // Test specific Provider health
    testConnection: async (provider, key, url = "") => {
        try {
            const res = await fetch(`${API_BASE}/settings/test`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ provider, key, url }),
            });
            if (res.ok) {
                const data = await res.json();
                return { connected: data.connected, reason: data.reason || "Verification failed." };
            }
            return { connected: false, reason: `HTTP error ${res.status}` };
        } catch (error) {
            console.error("Error testing connection:", error);
            return { connected: false, reason: error.message || "Failed to send request to backend." };
        }
    },

    // Fetch Startup Radar list
    fetchStartups: async () => {
        try {
            const res = await fetch(`${API_BASE}/startups/radar`);
            if (res.ok) {
                const data = await res.json();
                set({ startups: data });
            }
        } catch (error) {
            console.error("Error fetching startups radar:", error);
        }
    },

    // Scrape/discover more startups dynamically
    scrapeMoreStartups: async () => {
        set({ isLoadingMoreStartups: true });
        try {
            const res = await fetch(`${API_BASE}/startups/radar/scrape-more`, {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            });
            if (res.ok) {
                const data = await res.json();
                set({ startups: data });
                return true;
            }
            return false;
        } catch (error) {
            console.error("Error scraping more startups:", error);
            return false;
        } finally {
            set({ isLoadingMoreStartups: false });
        }
    },

    // Fetch Filter Options from Backend
    fetchFilterOptions: async () => {
        try {
            const res = await fetch(`${API_BASE}/filter-options`);
            if (res.ok) {
                const data = await res.json();
                set({ filterOptions: data });
            }
        } catch (error) {
            console.error("Error fetching filter options:", error);
        }
    },

    // Apply active job filters to jobs pool
    applyFilters: async (customFilters = null) => {
        set({ isLoading: true });
        const filters = customFilters || get().activeFilters;
        try {
            const res = await fetch(`${API_BASE}/jobs/filter`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(filters)
            });
            if (res.ok) {
                const data = await res.json();
                set({ jobs: data, activeFilters: filters });
            }
        } catch (error) {
            console.error("Error applying filters:", error);
        } finally {
            set({ isLoading: false });
        }
    },

    // Update single filter value and auto-apply
    updateFilter: async (name, value) => {
        const nextFilters = { ...get().activeFilters, [name]: value };
        await get().applyFilters(nextFilters);
    },

    // Reset filters to defaults and reload jobs pool
    resetFilters: async () => {
        const defaultFilters = {
            locations: [],
            work_modes: [],
            company_types: [],
            experience_levels: [],
            tiers: ["A", "B"],
            sources: [],
            min_salary: null,
            posted_within_days: null,
            fresher_compatibility: "All"
        };
        set({ activeFilters: defaultFilters });
        await get().applyFilters(defaultFilters);
    },

    // Fetch Resume Versions
    fetchResumes: async () => {
        try {
            const res = await fetch(`${API_BASE}/profile/resumes`);
            if (res.ok) {
                const data = await res.json();
                set({ resumes: data });
            }
        } catch (error) {
            console.error("Error fetching resumes:", error);
        }
    },

    // Save Resume Versions
    saveResumes: async (resumesData) => {
        set({ isLoading: true });
        try {
            const res = await fetch(`${API_BASE}/profile/resumes`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(resumesData),
            });
            if (res.ok) {
                set({ resumes: resumesData });
            }
        } catch (error) {
            console.error("Error saving resumes:", error);
        } finally {
            set({ isLoading: false });
        }
    },

    // Fetch Application Queue
    fetchQueue: async () => {
        try {
            const res = await fetch(`${API_BASE}/automation/queue`);
            if (res.ok) {
                const data = await res.json();
                set({ queue: data });
            }
        } catch (error) {
            console.error("Error fetching queue:", error);
        }
    },

    // Update Application Queue Status
    updateQueueStatus: async (jobId, status) => {
        try {
            const res = await fetch(`${API_BASE}/automation/queue`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ job_id: jobId, status }),
            });
            if (res.ok) {
                const data = await res.json();
                set({ queue: data.queue });
                get().fetchJobs();
                get().fetchMetrics();
            }
        } catch (error) {
            console.error("Error updating queue status:", error);
        }
    },

    // Fetch Career Metrics & Audit Logs
    fetchMetrics: async () => {
        try {
            const res = await fetch(`${API_BASE}/automation/metrics`);
            if (res.ok) {
                const data = await res.json();
                set({ metrics: data });
            }
        } catch (error) {
            console.error("Error fetching metrics:", error);
        }
    },

    // Fetch Strict Validation Report
    fetchValidationReport: async () => {
        try {
            const res = await fetch(`${API_BASE}/validation/report`);
            if (res.ok) {
                const data = await res.json();
                if (data && data.stats) {
                    set({
                        validationReport: {
                            ...data.stats,
                            history: data.history || []
                        }
                    });
                } else {
                    set({ validationReport: { ...data, history: [] } });
                }
            }
        } catch (error) {
            console.error("Error fetching validation report:", error);
        }
    },

    // Delete and reset all local files and store states
    resetAllData: async () => {
        set({ isLoading: true });
        try {
            const res = await fetch(`${API_BASE}/data/reset`, {
                method: "POST"
            });
            if (res.ok) {
                // Clear store state
                set({
                    profile: {
                        name: "",
                        email: "",
                        phone: "",
                        location: "",
                        target_roles: [],
                        skills: [],
                        salary_expectation: 0,
                        base_resume: "",
                        experience_level: "Fresher",
                        preferred_work_mode: "Remote",
                        region: "Kerala",
                        ai_instructions: "",
                        preferred_company_types: [],
                        excluded_company_types: [],
                        global_rules: "",
                        temporary_search_rules: "",
                    },
                    validationReport: {
                        jobs_collected: 0,
                        jobs_rejected: 0,
                        jobs_displayed: 0,
                        duplicates_removed: 0,
                        scams_blocked: 0,
                        training_institutes_blocked: 0,
                        experience_rejected: 0,
                        rejection_categories: {},
                        top_failure_reasons: []
                    },
                    settings: {
                        active_provider: "openai",
                        openai_api_key: "",
                        groq_api_key: "",
                        gemini_api_key: "",
                        ollama_url: "http://localhost:11434",
                        source_adzuna: true,
                        source_jooble: true,
                        source_manual_import: false,
                        source_company_careers: true,
                    },
                    jobs: [],
                    startups: [],
                    isLoadingMoreStartups: false,
                    activeFilters: {
                        locations: [],
                        work_modes: [],
                        company_types: [],
                        experience_levels: [],
                        tiers: ["A", "B"],
                        sources: [],
                        min_salary: null,
                        posted_within_days: null,
                        fresher_compatibility: "All"
                    },
                    filterOptions: {
                        locations: [],
                        company_types: [],
                        experience_levels: [],
                        sources: []
                    },
                    resumes: {},
                    queue: { applications: {}, audit_logs: [] },
                    metrics: { total_submitted: 0, interview_rate: 0.0, offer_rate: 0.0, best_source: "N/A", best_resume: "N/A", audit_logs: [] },
                    nodes: [],
                    edges: [],
                    activeTab: "dashboard"
                });
                return true;
            }
            return false;
        } catch (error) {
            console.error("Error resetting data:", error);
            throw error;
        } finally {
            set({ isLoading: false });
        }
    },
}));
