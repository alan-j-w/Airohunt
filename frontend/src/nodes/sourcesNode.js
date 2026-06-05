import React from "react";
import BaseNode from "../components/BaseNode";
import { useStore } from "../store";

const SourcesNode = ({ id, data }) => {
  const updateNodeField = useStore((state) => state.updateNodeField);
  
  const sourceAdzuna = data?.sourceAdzuna !== false; // default true
  const sourceJooble = data?.sourceJooble !== false; // default true
  const sourceManualImport = data?.sourceManualImport === true; // default false
  const sourceCompanyCareers = data?.sourceCompanyCareers !== false; // default true

  return (
    <BaseNode
      title="Job Sources Selection"
      inputs={[{ id: "in", label: "Input" }]}
      outputs={[{ id: "out", label: "Jobs Feed" }]}
      headerBg="bg-blue-600"
      borderColor="border-blue-600/40"
    >
      <div className="space-y-2 text-xs">
        <label className="flex items-center justify-between cursor-pointer p-1.5 bg-slate-950/40 rounded border border-slate-800/80 hover:border-slate-800 transition-colors">
          <span className="text-slate-300 font-semibold">Adzuna API</span>
          <input
            type="checkbox"
            checked={sourceAdzuna}
            onChange={(e) => updateNodeField(id, "sourceAdzuna", e.target.checked)}
            className="rounded bg-slate-950 border-slate-800 text-blue-500 focus:ring-blue-500 w-3.5 h-3.5 cursor-pointer"
          />
        </label>
        
        <label className="flex items-center justify-between cursor-pointer p-1.5 bg-slate-950/40 rounded border border-slate-800/80 hover:border-slate-800 transition-colors">
          <span className="text-slate-300 font-semibold">Jooble API</span>
          <input
            type="checkbox"
            checked={sourceJooble}
            onChange={(e) => updateNodeField(id, "sourceJooble", e.target.checked)}
            className="rounded bg-slate-950 border-slate-800 text-blue-500 focus:ring-blue-500 w-3.5 h-3.5 cursor-pointer"
          />
        </label>

        <label className="flex items-center justify-between cursor-pointer p-1.5 bg-slate-950/40 rounded border border-slate-800/80 hover:border-slate-800 transition-colors">
          <span className="text-slate-300 font-semibold">Startup Radar</span>
          <input
            type="checkbox"
            checked={sourceCompanyCareers}
            onChange={(e) => updateNodeField(id, "sourceCompanyCareers", e.target.checked)}
            className="rounded bg-slate-950 border-slate-800 text-blue-500 focus:ring-blue-500 w-3.5 h-3.5 cursor-pointer"
          />
        </label>

        <label className="flex items-center justify-between cursor-pointer p-1.5 bg-slate-950/40 rounded border border-slate-800/80 hover:border-slate-800 transition-colors">
          <span className="text-slate-400 font-medium">Offline Imports</span>
          <input
            type="checkbox"
            checked={sourceManualImport}
            onChange={(e) => updateNodeField(id, "sourceManualImport", e.target.checked)}
            className="rounded bg-slate-950 border-slate-800 text-blue-500 focus:ring-blue-500 w-3.5 h-3.5 cursor-pointer"
          />
        </label>
      </div>
    </BaseNode>
  );
};

export default SourcesNode;
