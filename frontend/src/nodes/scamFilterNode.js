import React from "react";
import BaseNode from "../components/BaseNode";
import { useStore } from "../store";

const ScamFilterNode = ({ id, data }) => {
  const updateNodeField = useStore((state) => state.updateNodeField);
  const scamMode = data?.scamMode || "balanced";

  return (
    <BaseNode
      title="Anti-Scam Filter"
      inputs={[{ id: "jobs_in", label: "Jobs In" }]}
      outputs={[{ id: "jobs_out", label: "Safe Jobs" }]}
      headerBg="bg-rose-500"
      borderColor="border-rose-500/40"
    >
      <div className="space-y-3 text-xs">
        <div>
          <label className="text-slate-400 font-bold block mb-1 font-semibold">
            Anti-Scam Mode
          </label>
          <select
            value={scamMode}
            onChange={(e) => updateNodeField(id, "scamMode", e.target.value)}
            className="w-full p-2 rounded bg-slate-950 text-white border border-slate-800 focus:outline-none focus:border-rose-500 cursor-pointer"
          >
            <option value="balanced">Balanced (Flag & Reduce Score)</option>
            <option value="strict">Strict (Hide Suspected Scams)</option>
            <option value="off">Off (Disable Anti-Scam Rules)</option>
          </select>
        </div>
        
        <p className="text-[10px] text-slate-500 leading-normal">
          Filters out job posts requiring training fees, equipment purchases, or course vouchers. Strict mode hides them entirely. Balanced mode displays warning badges.
        </p>
      </div>
    </BaseNode>
  );
};

export default ScamFilterNode;

