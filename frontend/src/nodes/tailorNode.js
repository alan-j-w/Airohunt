import React from "react";
import BaseNode from "../components/BaseNode";
import { useStore } from "../store";

const TailorNode = ({ id, data }) => {
  const updateNodeField = useStore((state) => state.updateNodeField);
  const modelType = data?.modelType || "local";

  return (
    <BaseNode
      title="Resume Tailoring"
      inputs={[{ id: "jobs_in", label: "Jobs In" }]}
      outputs={[{ id: "jobs_out", label: "Tailored" }]}
      headerBg="bg-purple-500"
      borderColor="border-purple-500/40"
    >
      <div className="space-y-2 text-xs">
        <div>
          <label className="text-slate-400 font-bold block mb-1">Tailor Model</label>
          <select
            value={modelType}
            onChange={(e) => updateNodeField(id, "modelType", e.target.value)}
            className="w-full p-2 rounded bg-slate-950 text-white border border-slate-800 focus:outline-none focus:border-purple-500 cursor-pointer"
          >
            <option value="local">Local Heuristics (Free)</option>
            <option value="openai">OpenAI GPT-4o-mini</option>
            <option value="groq">Groq LLaMA 3</option>
            <option value="gemini">Gemini 1.5 Pro</option>
          </select>
        </div>
        <p className="text-[10px] text-slate-500 leading-normal">
          Highlight user skills and match keywords. Prohibits inventing credentials.
        </p>
      </div>
    </BaseNode>
  );
};

export default TailorNode;

