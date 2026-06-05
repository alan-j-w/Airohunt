import React from "react";

export const PipelineToolbar = () => {
    const nodeTypes = [
        { type: "jobSearchTrigger", label: "Job Search", category: "Trigger", color: "bg-cyan-500 hover:bg-cyan-400 text-black border-cyan-400" },
        { type: "jobSources", label: "Job Sources", category: "Trigger", color: "bg-blue-600 hover:bg-blue-500 text-white border-blue-500" },
        { type: "preferenceFilter", label: "AI Preferences", category: "Filter", color: "bg-teal-600 hover:bg-teal-500 text-white border-teal-500" },
        { type: "salaryFilter", label: "Salary Filter", category: "Filter", color: "bg-amber-500 hover:bg-amber-400 text-black border-amber-400" },
        { type: "scamFilter", label: "Anti-Scam", category: "Filter", color: "bg-rose-500 hover:bg-rose-400 text-white border-rose-400" },
        { type: "skillMatch", label: "Skills Matcher", category: "Filter", color: "bg-emerald-500 hover:bg-emerald-400 text-black border-emerald-400" },
        { type: "opportunityRanker", label: "Opportunity Ranker", category: "Logic", color: "bg-indigo-600 hover:bg-indigo-500 text-white border-indigo-500" },
        { type: "resumeScore", label: "Resume Scorer", category: "Logic", color: "bg-indigo-500 hover:bg-indigo-400 text-white border-indigo-400" },
        { type: "resumeTailor", label: "Resume Tailoring", category: "Logic", color: "bg-purple-500 hover:bg-purple-400 text-white border-purple-400" },
        { type: "appSubmit", label: "Submit Apply", category: "Action", color: "bg-teal-500 hover:bg-teal-400 text-black border-teal-400" },
    ];

    const onDragStart = (event, nodeType) => {
        const appData = {
            nodeType,
        };

        event.dataTransfer.setData(
            "application/reactflow",
            JSON.stringify(appData)
        );

        event.dataTransfer.effectAllowed = "move";
    };

    return (
        <div className="flex flex-wrap gap-3 p-4 border-b border-slate-800 bg-slate-900 shadow-inner">
            {nodeTypes.map((node) => (
                <div
                    key={node.type}
                    draggable
                    onDragStart={(event) => onDragStart(event, node.type)}
                    className={`
                        px-4 py-2 rounded-xl font-bold cursor-grab flex flex-col items-start gap-0.5 border shadow-sm
                        transition-all duration-300 hover:scale-105 active:cursor-grabbing select-none ${node.color}
                    `}
                >
                    <span className="text-xs leading-none">{node.label}</span>
                    <span className="text-[8px] opacity-70 tracking-widest uppercase font-black mt-0.5">{node.category}</span>
                </div>
            ))}
        </div>
    );
};
export default PipelineToolbar;