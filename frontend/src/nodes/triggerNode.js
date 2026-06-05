import React from "react";
import BaseNode from "../components/BaseNode";
import { useStore } from "../store";

const TriggerNode = ({ id, data }) => {
  const updateNodeField = useStore((state) => state.updateNodeField);
  const keywords = data?.keywords || "Software Engineer";
  const location = data?.location || "Remote";

  return (
    <BaseNode
      title="Job Search Trigger"
      outputs={[{ id: "jobs", label: "Job Feed" }]}
      headerBg="bg-cyan-500"
      borderColor="border-cyan-500/40"
    >
      <div className="space-y-2 text-xs">
        <div>
          <label className="text-slate-400 font-bold block mb-1">Keywords</label>
          <input
            value={keywords}
            onChange={(e) => updateNodeField(id, "keywords", e.target.value)}
            className="w-full p-2 rounded bg-slate-950 text-white border border-slate-800 focus:outline-none focus:border-cyan-500 transition-colors"
            placeholder="e.g. React Developer"
          />
        </div>
        <div>
          <label className="text-slate-400 font-bold block mb-1">Location</label>
          <input
            value={location}
            onChange={(e) => updateNodeField(id, "location", e.target.value)}
            className="w-full p-2 rounded bg-slate-950 text-white border border-slate-800 focus:outline-none focus:border-cyan-500 transition-colors"
            placeholder="e.g. Remote"
          />
        </div>
      </div>
    </BaseNode>
  );
};

export default TriggerNode;
