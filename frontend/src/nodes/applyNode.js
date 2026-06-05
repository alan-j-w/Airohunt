import React from "react";
import BaseNode from "../components/BaseNode";
import { useStore } from "../store";

const ApplyNode = ({ id, data }) => {
  const updateNodeField = useStore((state) => state.updateNodeField);
  const automationMode = data?.automationMode || "Assisted Apply";

  return (
    <BaseNode
      title="Application Submit"
      inputs={[{ id: "jobs_in", label: "Jobs In" }]}
      headerBg="bg-teal-500"
      borderColor="border-teal-500/40"
    >
      <div className="space-y-3 text-xs">
        <div>
          <label className="text-slate-400 font-bold block mb-1">Automation Mode</label>
          <select
            value={automationMode}
            onChange={(e) => updateNodeField(id, "automationMode", e.target.value)}
            className="w-full p-2 rounded bg-slate-950 text-white border border-slate-800 focus:outline-none focus:border-teal-500 cursor-pointer"
          >
            <option value="Assisted Apply">Assisted Apply (Helper Overlay)</option>
            <option value="Quick Apply">Quick Apply (Auto-Fill Script)</option>
            <option value="Disabled">Disabled (Manual Only)</option>
          </select>
        </div>
        
        <p className="text-[10px] text-slate-500 leading-normal font-medium">
          {automationMode === "Assisted Apply" && "Prepares tailored resume + highlights custom form questions."}
          {automationMode === "Quick Apply" && "Generates copy-paste JavaScript script to auto-fill common forms (Greenhouse, Lever, etc.)."}
          {automationMode === "Disabled" && "Disables helper scripts; track outcomes manually."}
        </p>
      </div>
    </BaseNode>
  );
};

export default ApplyNode;

