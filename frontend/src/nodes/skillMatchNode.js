import React from "react";
import BaseNode from "../components/BaseNode";
import { useStore } from "../store";

const SkillMatchNode = ({ id, data }) => {
  const updateNodeField = useStore((state) => state.updateNodeField);
  const minMatchPercent = data?.minMatchPercent || 50;

  return (
    <BaseNode
      title="Skills Matcher"
      inputs={[{ id: "jobs_in", label: "Jobs In" }]}
      outputs={[{ id: "jobs_out", label: "Matched Jobs" }]}
      headerBg="bg-emerald-500"
      borderColor="border-emerald-500/40"
    >
      <div className="space-y-2 text-xs">
        <div>
          <label className="text-slate-400 font-bold block mb-1">
            Min Skill Match: {minMatchPercent}%
          </label>
          <input
            type="range"
            min="0"
            max="100"
            step="10"
            value={minMatchPercent}
            onChange={(e) => updateNodeField(id, "minMatchPercent", e.target.value)}
            className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />
        </div>
        <p className="text-[10px] text-slate-500 leading-normal">
          Compares job description skills list with candidate profile skills.
        </p>
      </div>
    </BaseNode>
  );
};

export default SkillMatchNode;
