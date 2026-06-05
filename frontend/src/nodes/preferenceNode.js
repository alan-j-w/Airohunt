import React from "react";
import BaseNode from "../components/BaseNode";
import { useStore } from "../store";

const PreferenceNode = ({ id, data }) => {
  const updateNodeField = useStore((state) => state.updateNodeField);
  const aiInstructions = data?.aiInstructions || "";

  return (
    <BaseNode
      title="AI Preferences"
      inputs={[{ id: "pref_in", label: "Input" }]}
      outputs={[{ id: "pref_out", label: "Rules Out" }]}
      headerBg="bg-teal-600"
      borderColor="border-teal-600/40"
    >
      <div className="space-y-2 text-xs">
        <div>
          <label className="text-slate-400 font-bold block mb-1">
            Session Override Rules
          </label>
          <textarea
            value={aiInstructions}
            onChange={(e) => updateNodeField(id, "aiInstructions", e.target.value)}
            placeholder="e.g. Only React roles in Kochi. Avoid bonds. Minimum 3 LPA."
            rows={4}
            className="w-full p-2.5 rounded bg-slate-950 text-white border border-slate-800 focus:outline-none focus:border-teal-500 resize-none font-sans"
          />
        </div>
        <p className="text-[9px] text-slate-500 leading-normal">
          Overrides global profile instructions while this node remains active on the canvas.
        </p>
      </div>
    </BaseNode>
  );
};

export default PreferenceNode;
