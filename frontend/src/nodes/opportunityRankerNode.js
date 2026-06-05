import React from "react";
import BaseNode from "../components/BaseNode";
import { useStore } from "../store";

const OpportunityRankerNode = ({ id, data }) => {
  const updateNodeField = useStore((state) => state.updateNodeField);
  const startupWeight = data?.startupWeight || "Medium";
  const remoteWeight = data?.remoteWeight || "Medium";
  const salaryWeight = data?.salaryWeight || "Medium";
  const trustWeight = data?.trustWeight || "Medium";

  const options = ["Low", "Medium", "High"];

  return (
    <BaseNode
      title="Opportunity Ranker"
      inputs={[{ id: "jobs_in", label: "Jobs In" }]}
      outputs={[{ id: "jobs_out", label: "Ranked" }]}
      headerBg="bg-indigo-600"
      borderColor="border-indigo-600/40"
    >
      <div className="space-y-2.5 text-xs">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-slate-400 font-bold block mb-1">Startup Weight</label>
            <select
              value={startupWeight}
              onChange={(e) => updateNodeField(id, "startupWeight", e.target.value)}
              className="w-full p-2 rounded bg-slate-950 text-white border border-slate-800 focus:outline-none focus:border-indigo-500 cursor-pointer"
            >
              {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
            </select>
          </div>
          <div>
            <label className="text-slate-400 font-bold block mb-1">Remote Weight</label>
            <select
              value={remoteWeight}
              onChange={(e) => updateNodeField(id, "remoteWeight", e.target.value)}
              className="w-full p-2 rounded bg-slate-950 text-white border border-slate-800 focus:outline-none focus:border-indigo-500 cursor-pointer"
            >
              {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
            </select>
          </div>
          <div>
            <label className="text-slate-400 font-bold block mb-1">Salary Weight</label>
            <select
              value={salaryWeight}
              onChange={(e) => updateNodeField(id, "salaryWeight", e.target.value)}
              className="w-full p-2 rounded bg-slate-950 text-white border border-slate-800 focus:outline-none focus:border-indigo-500 cursor-pointer"
            >
              {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
            </select>
          </div>
          <div>
            <label className="text-slate-400 font-bold block mb-1">Trust Weight</label>
            <select
              value={trustWeight}
              onChange={(e) => updateNodeField(id, "trustWeight", e.target.value)}
              className="w-full p-2 rounded bg-slate-950 text-white border border-slate-800 focus:outline-none focus:border-indigo-500 cursor-pointer"
            >
              {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
            </select>
          </div>
        </div>
        <p className="text-[9px] text-slate-500 leading-normal">
          Adjusts the contribution of startup status, remote work, salary disclosure, and trust signs to the ranking score.
        </p>
      </div>
    </BaseNode>
  );
};

export default OpportunityRankerNode;
